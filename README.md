# 🚪 Dynamic Lab Environment on AWS EKS

This project sets up a **secure, dynamic Kubernetes lab environment** on **AWS EKS**. Each user gets their own isolated pod on demand, authenticated via OAuth2 (Google/GitHub), and routed through HTTPS via AWS ALB.

---

## 🚀 Features

- 🔐 Secure OAuth2 authentication
- 🧑‍💻 Dynamic user-based pod creation
- 🌐 HTTPS with AWS Application Load Balancer (ALB)
- 📦 FastAPI-based pod spawner
- 🛡️ Namespace isolation with RBAC and NetworkPolicy
- ☁️ High Availability with managed EKS

---

## 📋 Prerequisites

- AWS CLI
- `eksctl`
- `kubectl`
- `helm`
- Docker
- A domain name (preferably in Route53)
- ACM certificate for HTTPS
- OAuth2 credentials (Google or GitHub)

---

## 🏗️ Deployment Steps

### 1️⃣ Create EKS Cluster

```bash
eksctl create cluster \
  --name lab-cluster \
  --region us-west-2 \
  --nodegroup-name lab-nodes \
  --nodes 3 \
  --managed
```

---

### 2️⃣ Install AWS Load Balancer Controller

```bash
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=lab-cluster \
  --set serviceAccount.create=false \
  --set region=us-west-2 \
  --set vpcId=<your-vpc-id> \
  --set serviceAccount.name=aws-load-balancer-controller
```

---

### 3️⃣ Deploy OAuth2 Proxy

#### 🔐 Create Secret

```bash
kubectl create secret generic oauth2-proxy-secret \
  --from-literal=client-id=<CLIENT_ID> \
  --from-literal=client-secret=<CLIENT_SECRET> \
  --from-literal=cookie-secret=$(openssl rand -base64 32)
```

#### 📄 Apply OAuth2 Proxy Manifest

> Customize and apply `oauth2-proxy.yaml` with the appropriate values.

---

### 4️⃣ Deploy Pod Spawner (FastAPI)

#### 📦 Build & Push Docker Image

```bash
docker build -t pod-spawner .
aws ecr create-repository --repository-name pod-spawner
docker tag pod-spawner:latest <ECR_REPO_URL>
docker push <ECR_REPO_URL>
```

#### 🛠️ Deploy in Kubernetes

Create `pod-spawner.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pod-spawner
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pod-spawner
  template:
    metadata:
      labels:
        app: pod-spawner
    spec:
      containers:
        - name: pod-spawner
          image: <ECR_REPO_URL>
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: pod-spawner
spec:
  selector:
    app: pod-spawner
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
```

```bash
kubectl apply -f pod-spawner.yaml
```

---

### 5️⃣ Set Up HTTPS Ingress

#### 📄 Ingress Example

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: lab-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS": 443}]'
    alb.ingress.kubernetes.io/certificate-arn: <YOUR_ACM_ARN>
    alb.ingress.kubernetes.io/ssl-redirect: '443'
spec:
  rules:
    - host: <your.domain.com>
      http:
        paths:
          - path: /*
            pathType: ImplementationSpecific
            backend:
              service:
                name: oauth2-proxy
                port:
                  number: 4180
```

```bash
kubectl apply -f ingress.yaml
```

---

### 6️⃣ Add Domain & HTTPS

- Update your Route53 domain or DNS provider to point to the ALB DNS.
- Ensure ACM certificate is valid and DNS-verified.

---

## 🧪 Test Your Setup

1. Open browser → `https://your.domain.com`
2. Login with Google/GitHub
3. OAuth2 proxy forwards request to FastAPI
4. FastAPI:
   - Creates user namespace
   - Applies RBAC & NetworkPolicy
   - Spins up lab pod with PVC (if required)
   - Redirects user to their pod via subdomain

---

## 🛡️ Security Recommendations

- Use NetworkPolicy to restrict inter-namespace traffic.
- Auto-expire user pods after inactivity.
- Log and audit pod spawns and access.
- Rotate OAuth and cookie secrets periodically.

---

## 🛠️ Optional Enhancements

- Add OPA/Gatekeeper for security policies
- Auto-scale nodes with Cluster Autoscaler
- Add Prometheus/Grafana for metrics

---

## 📄 License

MIT © Nitin Mahajan
nitinneet23@gmail.com

