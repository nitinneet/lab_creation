  User hits ALB (HTTPS)
         │
         ▼
  OAuth2 Proxy (auth via Google/GitHub)
         │
         ▼
  Pod Spawner Webhook (Python/FastAPI)
         │
         ├─> Check if namespace exists
         ├─> If not, create namespace, RBAC, NetworkPolicy
         └─> Spin up Pod with PVC if needed
         ▼
     Redirect to user-specific subdomain/pod

###################################################

Feature | Tool
Authentication: OAuth2 Proxy / Keycloak
Namespace Isolation: Kubernetes native
Dynamic Provisioning: Python app / controller
HTTPS + WAF | AWS ALB + ACM + WAF
Storage: AWS EFS or ephemeral
Monitoring: CloudWatch / Prometheus
Cleanup: TTLController / CronJob

#####################################################
Prerequisites:

AWS CLI & IAM Authenticator
kubectl
eksctl
Helm
A domain name (e.g. via Route53)
OAuth2 client (Google or GitHub)
SSL certificate (AWS ACM)

Step 1: Create Your EKS Cluster
eksctl create cluster \
  --name lab-cluster \
  --region us-west-2 \
  --nodegroup-name lab-nodes \
  --nodes 3 \
  --managed

Step 2: Install NGINX Ingress Controller (with ALB Support)
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=lab-cluster \
  --set serviceAccount.create=false \
  --set region=us-west-2 \
  --set vpcId=<your-vpc-id> \
  --set image.repository=602401143452.dkr.ecr.us-west-2.amazonaws.com/amazon/aws-load-balancer-controller \
  --set serviceAccount.name=aws-load-balancer-controller

Step 3: Deploy OAuth2 Proxy
kubectl create secret generic oauth2-proxy-secret \
  --from-literal=client-id=<YOUR_CLIENT_ID> \
  --from-literal=client-secret=<YOUR_CLIENT_SECRET> \
  --from-literal=cookie-secret=$(openssl rand -base64 32)

Apply OAuth2 proxy manifests (see Deployment manifest file).
Make sure your Ingress routes /oauth2 to the OAuth2 proxy service.

Step 4: Deploy the Pod Spawner API
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9
COPY ./app /app

Build & push to ECR:
docker build -t pod-spawner .
aws ecr create-repository --repository-name pod-spawner
docker tag pod-spawner:latest <ECR_REPO_URL>
docker push <ECR_REPO_URL>

Create Kubernetes Deployment & Service: (podspawner.yml)

Step 5: Setup Ingress and HTTPS (ACM + ALB)
Create an ACM cert for your domain.
Use annotations in Ingress for AWS ALB:
metadata:
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: <YOUR_ACM_CERT_ARN>

Step 6: Add Security Controls
Enable RBAC in each user namespace dynamically.
Enforce NetworkPolicy per namespace (e.g. block cross-talk).
Use PodSecurityPolicies or OPA/Gatekeeper for fine-grained control (optional).

