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
    queue = sqs.Queue(os.environ.get('queue_arn'))
    
    all_emails = boto3.resource('dynamodb').Table('tokens').scan(ProjectionExpression='email')['Items']

    
    for email_dict in all_emails:
        email = email_dict['email']
        filter = f""" WHERE email='{email}' AND CAST("timestamp" AS INT) < {int(time())} AND CAST("timestamp" AS INT) > {int(time())- (3600 * 24 * 7)} """
        plays_query = "SELECT name, COUNT(*), SUM(duration_seconds) AS total_time, image FROM listening_history" + filter +  "GROUP BY (name, image) ORDER BY total_time DESC LIMIT 5"
        plays_results = queryAthena(athena, plays_query)
        duration_query = "SELECT SUM(duration_seconds) FROM listening_history" + filter
        duration_results = queryAthena(athena, duration_query)
        artists_query = "SELECT artist, count(artist), sum(duration_seconds) as total FROM listening_history, unnest(artists) as t(artist)" + filter + "GROUP BY artist ORDER BY total DESC LIMIT 5"
        artists_results = queryAthena(athena, artists_query)

        response = {}
        response['email'] = email
        # the slicing excludes the headers row
        try:
            response['plays'] = [{'name':i['Data'][0]['VarCharValue'],'plays':i['Data'][1]['VarCharValue'],'duration':int(float(i['Data'][2]['VarCharValue'])//60),'image':i['Data'][3]['VarCharValue']} for i in plays_results['ResultSet']['Rows'][1:]]
            response['artists'] = [{'name':i['Data'][0]['VarCharValue'],'plays':i['Data'][1]['VarCharValue'],'duration':int(float(i['Data'][2]['VarCharValue'])//60)} for i in artists_results['ResultSet']['Rows'][1:]]
            response['minutes_played'] = int(float(duration_results['ResultSet']['Rows'][1]['Data'][0]['VarCharValue'])//60)
            queue.send_message(MessageBody = json.dumps(response))
        except KeyError as e:
            print(e)
            return
 
    return response
