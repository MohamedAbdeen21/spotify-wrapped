from time import sleep,time
import boto3
import json
import os

def queryAthena(athena, query):
    execution_id = athena.start_query_execution(
            QueryString=query,
        QueryExecutionContext={"Database": "default", "Catalog": "listening_history"},
        ResultConfiguration={"OutputLocation": "s3://spotify-wrapped-spill/test/"},
    )["QueryExecutionId"]

    while athena.get_query_execution(QueryExecutionId=execution_id)['QueryExecution']['Status']['State'] in ['RUNNING','QUEUED']:
        sleep(2)

    return athena.get_query_results(QueryExecutionId=execution_id)

def lambda_handler(event, context):
    athena = boto3.client("athena")
    sqs = boto3.resource("sqs")
    queue = sqs.Queue(os.environ.get('queue'))
    
    all_emails = boto3.resource('dynamodb').Table('tokens').scan(ProjectionExpression='email')['Items']

    
    for email_dict in all_emails:
        email = email_dict['email']
        filter = f""" WHERE email='{email}' AND CAST("timestamp" AS INT) < {int(time())} AND CAST("timestamp" AS INT) > {int(time())- (3600 * 24)} """
        plays_query = "SELECT name, COUNT(*) AS total_plays FROM listening_history" + filter +  "GROUP BY (name) ORDER BY total_plays DESC LIMIT 10"
        plays_results = queryAthena(athena, plays_query)
        duration_query = "SELECT SUM(duration_seconds) FROM listening_history" + filter
        duration_results = queryAthena(athena, duration_query)
    
        response = {}
        response['email'] = email
        # the slicing excludes the headers row
        try:
            response['plays'] = [{i['Data'][0]['VarCharValue']:i['Data'][1]['VarCharValue']} for i in plays_results['ResultSet']['Rows'][1:]]
            response['minutes_played'] = float(duration_results['ResultSet']['Rows'][1]['Data'][0]['VarCharValue'])//60
        except KeyError:
            response['plays'] = []
            response['minutes_played'] = 0
        finally:
            queue.send_message(MessageBody = json.dumps(response))
 
    return response

