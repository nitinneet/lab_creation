from fastapi import FastAPI, Request
from kubernetes import client, config
import hashlib

app = FastAPI()
config.load_incluster_config()
v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

def sanitize_username(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()[:10]

@app.get("/lab")
async def create_lab(request: Request):
    user_email = request.headers.get("X-Auth-Request-Email")
    if not user_email:
        return {"error": "Unauthorized"}

    namespace = f"lab-{sanitize_username(user_email)}"

    # Check if namespace exists
    try:
        v1.read_namespace(namespace)
    except client.exceptions.ApiException as e:
        if e.status == 404:
            # Create namespace
            ns = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
            v1.create_namespace(ns)

            # Create deployment
            container = client.V1Container(
                name="lab-container",
                image="your-lab-image",
                ports=[client.V1ContainerPort(container_port=80)]
            )
            template = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "lab"}),
                spec=client.V1PodSpec(containers=[container])
            )
            spec = client.V1DeploymentSpec(
                replicas=1,
                template=template,
                selector={'matchLabels': {'app': 'lab'}}
            )
            deployment = client.V1Deployment(
                metadata=client.V1ObjectMeta(name="lab-deployment"),
                spec=spec
            )
            apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)

            # Create service
            service = client.V1Service(
                metadata=client.V1ObjectMeta(name="lab-service"),
                spec=client.V1ServiceSpec(
                    selector={"app": "lab"},
                    ports=[client.V1ServicePort(protocol="TCP", port=80, target_port=80)]
                )
            )
            v1.create_namespaced_service(namespace=namespace, body=service)

    return {"message": f"Lab environment ready for {user_email}"}
