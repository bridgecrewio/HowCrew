# Setup GCP audit trail GCS bucket
Audit log data can be used to map and illustrate the following:
* conceptual relationships
* causes and effects
* interactions between GCP entities

And is useful to answer PCI needs such as tracking:
* Successful login
* Unsuccessful login
* Creating user
* Deleting user
* Adding user to strong groups (admin)


## Prerequisites:
* [Creating a service account](https://cloud.google.com/docs/authentication/production)
* Configure environment variable GOOGLE_APPLICATION_CREDENTIALS with file location
    ```bash
    export GOOGLE_APPLICATION_CREDENTIALS="~/creds.json"
    ```
* When you create a GCP Compliance Integration or GCP Audit Log Integration manually, 
you must enable APIs for the GCP projects you want to integrate with.
* [Enable KMS API]( https://console.developers.google.com/apis/api/cloudkms.googleapis.com/overview)
* [Enable IAM API](iam.googleapis.com)
* [Cloud Resource Manager API](cloudresourcemanager.googleapis.com)
* [Cloud Key Management Service (KMS) API](cloudkms.googleapis.com)
* [Compute Engine API](compute.googleapis.com)
* [Google Cloud DNS API](dns.googleapis.com)
* [Stackdriver Monitoring API](monitoring.googleapis.com)
* [Stackdriver Logging API](logging.googleapis.com)
* [Cloud Storage](storage-component.googleapis.com)
* [Service Usage API](serviceusage.googleapis.com)
* [Kubernetes Engine API](container.googleapis.com)
# Deployment

```bash
# Customize the following variables
export tag="feature-branch-foo"
export project="my-project"

# Create terraform remote state bucket
cd ./modules/backend_bucket/
terraform init --reconfigure
terraform apply -var "gcp_project=$project" --auto-approve
bucketname=$(terraform output -json | jq -r '.bucket_name.value')

# Apply project terraform
cd ../../
echo $PWD
terraform init -backend-config="bucket=$bucketname" --reconfigure
terraform apply -var "gcp_project=$project" -refresh=true -var "tag=$tag"
```
 