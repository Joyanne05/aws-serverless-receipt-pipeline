import json 
import boto3
import base64
import uuid 
from decimal import Decimal

# Initialize clients outside the handler for optimal speed 
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = 'receipt-ingest-pipeline'
TABLE_NAME = 'Receipts'
table = dynamodb.Table(TABLE_NAME)

def decimal_default(obj): 
    if isinstance(obj, Decimal): 
        return float(obj)
    raise TypeError 

def lambda_handler(event, context): 
    # Detect the HTTP method coming from API Gateway
    http_method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method')
    
    # Crucial CORS headers so your frontend application can communicate securely
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }

    # Handle Browser CORS Preflight Options check
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers, 'body': ''}

    try: 
        # POST route 
        if http_method == 'POST': 
            body = json.loads(event.get('body', '{}'))
            base64_image = body.get('image')

            if not base64_image: 
                return {'statusCode': 400, 'headers': cors_headers, 'body': json.dumps({'error': 'No image data provided'})}
            
            image_bytes = base64.b64decode(base64_image)
            filename = f"receipt-{uuid.uuid4()}jpeg"

            # Put image into s3 bucket
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=filename,
                Body=image_bytes,
                ContentType='image/jpeg'
            )

            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'message': 'Image uploaded successfully',
                    'filename': filename
                })
            }

        elif http_method == 'GET': 
            # GET receipts metadata 
            db_response = table.scan()
            items = db_response.get('Items', [])

            filtered_res = [] 
            for item in items: 
                cleaned_item = {
                    'receipt_id': item.get('receipt_id'), 
                    'merchant_name': item.get('merchant_name'),
                    'date': item.get('date'),
                    'total_amount': item.get('total_amount'),
                    'items': item.get('items', [])
                }
                filtered_res = filtered_res + [cleaned_item]

            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'receipts': filtered_res
                }, default=decimal_default)
            }

        # Method fallback guard
        return {
            'statusCode': 405,
            'headers': cors_headers,
            'body': json.dumps({'error': f'Method {http_method} not supported'})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': str(e)})
        }

