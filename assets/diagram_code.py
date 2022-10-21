from diagrams import Cluster, Diagram, Edge
from diagrams.aws.storage import S3
from diagrams.aws.analytics import Athena
from diagrams.aws.compute import Lambda
from diagrams.aws.integration import SimpleQueueServiceSqs as sqs
from diagrams.aws.database import Dynamodb
from diagrams.programming.framework import Fastapi
from diagrams.custom import Custom
from diagrams.aws.security import IAM
from diagrams.aws.management import Cloudwatch

with Diagram(direction="LR"):

    with Cluster("Access and monitoring", direction="TB"):
        IAM() >> Edge(color='white') >> Cloudwatch()

        with Cluster("Pipeline"):
            tokens = Dynamodb("Tokens")
            history = Dynamodb("History")

            with Cluster("Registeration", graph_attr={'labeljust':'C'}):
                api = Fastapi()
                register = Custom("Spotify API", "./spotify.png")
                api >> Edge(forward=True, reverse=True) >> register

            with Cluster("Load Recent Plays\n(Hourly Trigger)", graph_attr={"labeljust":"C"}):
                load = Lambda()
                spotify = Custom("Spotify API", "./spotify.png")

            with Cluster("Process, Publish and Archive\n(Weekly Trigger)", graph_attr={"labeljust":"C"}):
                query = Athena()
                aggregate = Lambda()

            with Cluster("Data Lake", graph_attr={'labeljust':'C'}):
                archive = S3()

            queue = sqs()
            send_emails = Lambda('send emails')

            load >> history
            load >> Edge(forward=True, reverse=True) >> spotify
            load >> Edge(forward=True, reverse=True) >> tokens
            history >> Edge(forward=True, reverse=True) >> query
            query >> Edge(forward=True, reverse=True) >> aggregate >> queue >> send_emails
            aggregate >> archive
            api >> tokens
