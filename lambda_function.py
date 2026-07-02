import json
import boto3
import os
from datetime import datetime

def replace_special_characters(input_string):
    updated_string = input_string.replace('&', '&amp;')
    updated_string = input_string.replace('"', '&quot;')
    updated_string = input_string.replace("'", '&apos;')
    updated_string = input_string.replace('<', '&lt;')
    updated_string = input_string.replace('>', '&gt;')
    return updated_string

def lambda_handler(event, context):
    print(event)

    event = json.loads(event["body"])

    # Check for 'ServiceManager' in the event
    if "ServiceManager" in event:
        service_manager = event["ServiceManager"]
        account_number = event["AccountNumber"]
        case_number = event["CaseNumber"]

        # Prepare params for Amazon Connect call
        params = {
            "ContactFlowId": "02207f0d-c49c-4eaf-86ff-eb24dc269112",
            "DestinationPhoneNumber": service_manager,
            "InstanceId": "672876cb-ec13-42cb-934c-946e6bfe7230",
            "QueueId": "72813f2d-b5b5-42e2-92ec-ba7c8aa54d7d",
            "Attributes": {
                "requestId": context.aws_request_id,
                "ServiceManager": str(service_manager),
                "AccountNumber": account_number,
                "CaseNumber": case_number
            },
            "SourcePhoneNumber": "+12678075272"
        }

        print(params)
        connect = boto3.client("connect")

        # Call Amazon Connect
        try:
            response = connect.start_outbound_voice_contact(**params)
            print(response)
            contact_id = response["ContactId"]

            # Optionally invoke AmazonConnecttoSNOW Lambda asynchronously
            try:
                lambda_client = boto3.client('lambda')
                snow_event = {
                    "ServiceManager": service_manager,
                    "AccountNumber": account_number,
                    "CaseNumber": case_number
                }
                lambda_response = lambda_client.invoke(
                    FunctionName='AmazonConnecttoSNOW',
                    InvocationType='Event',  # Asynchronous invocation
                    Payload=json.dumps(snow_event)
                )
                print("Response from AmazonConnecttoSNOW:", lambda_response)
            except Exception as snow_error:
                print(f"Error invoking AmazonConnecttoSNOW: {snow_error}")

            return {
                "statusCode": 200,
                "body": json.dumps({"ContactID": contact_id})
            }
        except connect.exceptions.DestinationNotAllowedException as e:
            print("Call failed:", e)
            return {
                "statusCode": 400,
                "body": "Call failed: " + str(e)
            }
        except Exception as e:
            print("Service error:", e)
            return {
                "statusCode": 500,
                "body": "Service error: " + str(e)
            }

    # Existing functionality for IBX_name
    elif "IBX_name" in event:
        ibx_name = event["IBX_name"]
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(os.environ["tableName"])
        response = table.get_item(Key={"IBX_Name": ibx_name})

        if "Item" in response:
            item = response["Item"]
            start_time = datetime.strptime(item.get('Start Time (UTC)', '8AM'), '%I%p').time()
            end_time = datetime.strptime(item.get('End Time (UTC)', '8PM'), '%I%p').time()
            current_time = datetime.utcnow().time()
            current_day = datetime.utcnow().weekday()

            if current_day <= 4 and start_time <= current_time <= end_time:
                ibx_number = item.get("IBX_Number")
            else:
                ibx_number = item.get("IBX_Secondary_Number") or item.get("IBX_Number")
            

            language = item.get("Language")
            escalationpath1 = item.get("EscalationPath1")
            escalationpath1_secondary = item.get("EscalationPath1_Secondary")
            account_name = replace_special_characters(event["accountName"])

            if "trigger" in event:
                params = {
                    "ContactFlowId": "eb088ba2-d35c-4c43-9185-18c94d6fc59a",
                    "DestinationPhoneNumber": ibx_number,
                    "InstanceId": "672876cb-ec13-42cb-934c-946e6bfe7230",
                    "QueueId": "72813f2d-b5b5-42e2-92ec-ba7c8aa54d7d",
                    "Attributes": {
                        "requestId": context.aws_request_id,
                        "IBX_Number": str(ibx_number),
                        "IBX_name": ibx_name,
                        "accountName": account_name,
                        "existingOrder": event["existingOrder"],
                        "trigger": event["trigger"],
                        "accountNumber": event["accountNumber"],
                        "language": str(language),
                        "EscalationPath1": str(escalationpath1),
                        "EscalationPath1_Secondary": str(escalationpath1_secondary),
                        "Cage": event["cage"]
                    },
                    "SourcePhoneNumber": "+12678075272"
                }
            else:
                params = {
                    "ContactFlowId": "eb088ba2-d35c-4c43-9185-18c94d6fc59a",
                    "DestinationPhoneNumber": ibx_number,
                    "InstanceId": "672876cb-ec13-42cb-934c-946e6bfe7230",
                    "QueueId": "72813f2d-b5b5-42e2-92ec-ba7c8aa54d7d",
                    "Attributes": {
                        "requestId": context.aws_request_id,
                        "IBX_Number": str(ibx_number),
                        "IBX_name": ibx_name,
                        "accountName": account_name,
                        "existingOrder": event["existingOrder"],
                        "accountNumber": event["accountNumber"],
                        "language": str(language),
                        "EscalationPath1": str(escalationpath1),
                        "EscalationPath1_Secondary": str(escalationpath1_secondary),
                        "Cage": event["cage"]
                    },
                    "SourcePhoneNumber": "+12678075272"
                }

            print(params)
            connect = boto3.client("connect")
            try:
                response = connect.start_outbound_voice_contact(**params)
                print(response)
                contact_id = response["ContactId"]
                return {
                    "statusCode": 200,
                    "body": json.dumps({"ContactID": contact_id})
                }
            except connect.exceptions.DestinationNotAllowedException as e:
                print("Call failed:", e)
                return {
                    "statusCode": 400,
                    "body": "Call failed: " + str(e)
                }
            except Exception as e:
                print("Service error:", e)
                return {
                    "statusCode": 500,
                    "body": "Service error: " + str(e)
                }
        else:
            return {"statusCode": 404, "body": "Item not found in DynamoDB"}

    else:
        return {"statusCode": 400, "body": "Invalid event payload"}
