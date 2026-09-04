from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct


class InfraStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ==========================================
        # 1. The Network Foundation (Amazon VPC)
        # ==========================================
        self.vpc = ec2.Vpc(
            self, "MdmVpc",
            max_azs=2,  # High availability across 2 Availability Zones
            nat_gateways=1,  # Allows private containers to pull Docker images from the internet
            subnet_configuration=[
                # The Public Subnet: For the Application Load Balancer (ALB)
                ec2.SubnetConfiguration(
                    name="PublicIngress",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                # The Private Subnet: For the ECS Fargate Containers
                ec2.SubnetConfiguration(
                    name="PrivateCompute",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
                # The Isolated Subnet: Strict lockdown for the PostgreSQL Database
                ec2.SubnetConfiguration(
                    name="IsolatedDatabase",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24
                )
            ]
        )

        # ==========================================
        # 2. The Persistence Layer (AWS RDS)
        # ==========================================
        self.db = rds.DatabaseInstance(
            self, "MdmPostgres",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16
            ),
            # Use a t3.micro to keep costs incredibly low
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.MICRO
            ),
            vpc=self.vpc,
            # Place the database in the Isolated Subnet (no internet access)
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
            database_name="mdm_db",
            # AWS Secrets Manager will automatically generate and rotate this password
            credentials=rds.Credentials.from_generated_secret("mdm_admin"),
            # For this dev project, destroy the DB if we delete the stack
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Output the Secret ARN so we can find the password later
        CfnOutput(
            self, "DatabaseSecretArn",
            value=self.db.secret.secret_arn
        )

        # ==========================================
        # 3. The Image Registry (AWS ECR)
        # ==========================================
        self.ecr_repo = ecr.Repository(
            self, "MdmApiRepository",
            repository_name="mdm-api-repo",
            # Automatically delete the repository if we destroy the stack
            removal_policy=RemovalPolicy.DESTROY,
            # CRITICAL: CDK cannot delete a repository if it has images inside it unless this is True
            empty_on_delete=True
        )

        # Output the ECR URI so we can easily tag and push our Docker image
        CfnOutput(
            self, "EcrRepositoryUri",
            value=self.ecr_repo.repository_uri
        )

        # ==========================================
        # 4. Compute & Load Balancer (ECS Fargate + ALB)
        # ==========================================
        self.ecs_cluster = ecs.Cluster(
            self, "MdmEcsCluster",
            vpc=self.vpc
        )

        # ApplicationLoadBalancedFargateService sets up the ECS service, task definition,
        # security groups, target group, and the public Application Load Balancer automatically.
        self.fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "MdmFargateService",
            cluster=self.ecs_cluster,
            cpu=256,  # 0.25 vCPU
            memory_limit_mib=512,  # 512 MB RAM
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_ecr_repository(self.ecr_repo, tag="latest"),
                container_port=8000,
                environment={
                    "DATABASE_HOST": self.db.db_instance_endpoint_address,
                    "DATABASE_PORT": "5432",
                    "DATABASE_NAME": "mdm_db"
                }
            ),
            public_load_balancer=True,
            assign_public_ip=False,
            # Place container tasks in the Private Compute subnets
            task_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            )
        )

        # Allow the Fargate container security group to talk to the RDS database security group on port 5432
        self.db.connections.allow_from(
            self.fargate_service.service,
            ec2.Port.tcp(5432),
            "Allow FastAPI containers to access PostgreSQL"
        )

        # Output the public URL of the Application Load Balancer
        CfnOutput(
            self, "LoadBalancerDNS",
            value=self.fargate_service.load_balancer.load_balancer_dns_name
        )
