import json
import boto3
import os
from decimal import Decimal

# Initialize AWS Clients
rekognition_client = boto3.client('rekognition')
bedrock_client = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Receipts')

def lambda_handler(event, context):
    try:
        # 1. Parse the incoming S3 bucket trigger details
        s3_record = event['Records'][0]['s3']
        bucket_name = s3_record['bucket']['name']
        object_key = s3_record['object']['key']
        
        print(f"Processing new file: {object_key} from bucket: {bucket_name}")
        
        # 2. Run Amazon Rekognition Text Detection (Visual OCR)
        ocr_response = rekognition_client.detect_text(
            Image={'S3Object': {'Bucket': bucket_name, 'Name': object_key}}
        )
        
        # Extract detected lines of text into a single cohesive string block
        detected_text_lines = [
            text_obj['DetectedText'] 
            for text_obj in ocr_response['TextDetections'] 
            if text_obj['Type'] == 'LINE'
        ]
        raw_receipt_string = "\n".join(detected_text_lines)
        
        print("Raw OCR extraction completed successfully.")

        # 3. Use Amazon Bedrock (Claude 4.6 Sonnet) to structure the raw messy text
        system_prompt = (
            "You are an expert financial receipt parser. Your job is to take raw text extracted from "
            "a messy receipt via OCR and organize it into a clean, valid JSON object. "
            "Respond ONLY with the raw JSON. Do not include markdown codeblocks (like ```json), intro text, or explanations."
        )
        
        user_prompt = f"""Analyze this raw text block from a receipt scan and structure it.
        Extract the following fields if present:
        - merchant_name
        - date
        - total_amount (as a number)
        - currency
        - total_savings
        - items (as a list/array of items with their individual prices if identifiable)

        Raw Receipt Text:
        {raw_receipt_string}
        """

        # Construct Bedrock standard payload for Claude
        body_payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.0,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ]
        }

        # Invoke model using cross-region inference endpoint for fast processing
        bedrock_response = bedrock_client.invoke_model(
            modelId="au.anthropic.claude-sonnet-4-6",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body_payload)
        )
        
        # Read and parse response from Bedrock
        response_body = json.loads(bedrock_response.get('body').read())
        ai_structured_string = response_body['content'][0]['text'].strip()
        
        # Convert string output to actual native Python dict
        structured_data = json.loads(ai_structured_string, parse_float=Decimal)

        total_val = structured_data.get('total_amount', 0.00)

        # 1. If it's a string, strip currencies, whitespace, and clean it up
        if isinstance(total_val, str): 
            total_val = total_val.replace('$', '').replace('USD', '').replace('AUD', '').strip()
            
        # 2. Defensive Guard: If total_val became empty, null, or is a non-numeric string (like "Unknown")
        try:
            if not total_val or str(total_val).strip() == "":
                total_val = Decimal('0.00')
            else:
                total_val = Decimal(str(total_val))
        except (ValueError, InvalidOperation, Exception):
            print(f"Warning: Could not parse total_val '{total_val}' to Decimal. Defaulting to 0.00")
            total_val = Decimal('0.00')

        # 4. Save Structured Receipt Data into DynamoDB Table
        # Use the filename key as the unique partition ID
        receipt_item = {
            'receipt_id': object_key,
            'merchant_name': structured_data.get('merchant_name', 'Unknown'),
            'date': structured_data.get('date', 'Unknown'),
            'total_amount': total_val, # DynamoDB handles decimal numbers smoothly as strings
            'currency': structured_data.get('currency', 'AUD'),
            'items': structured_data.get('items', []),
            'raw_ocr_metadata': raw_receipt_string[:2000] # Save a snippet of raw text for audit reference
        }
        
        table.put_item(Item=receipt_item)
        print(f"Successfully processed and stored receipt records for: {object_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps('Pipeline executed successfully!')
        }

    except Exception as e:
        print(f"Error occurring inside execution handler: {str(e)}")
        raise e