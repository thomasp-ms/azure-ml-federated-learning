# EXPERIMENTAL: run cross-geo distributed job in AzureML using Service Bus and Magic

## Provision using vnet peering

```bash
# connect to azure
az login
az account set --name "your subscription name"

# create resource group
az group create -n nvflare-devbox-rg -l eastus

# deploy vnet peered sandbox
az deployment group create --template-file .\mlops\bicep\vnet_publicip_sandbox_setup.bicep --resource-group nvflare-devbox-rg --parameters demoBaseName="nvflaredev1" applyVNetPeering=true
```

## Provision a Service Bus

1. Use Azure Portal to provision a Service Bus resource in the same resource group. Use Standard pricing tier. Name it `fldevsb` for instance.

2. Create a Topic `fldevsbtopic`, set time to live to 1h.

## Run sample

1. Install python dependencies

    ```bash
    conda create --name "servicebusenv" python=3.8 -y
    conda activate servicebusenv
    python -m pip install -r requirements.txt
    ```

2. Install az cli v2

    ```bash
    az extension add --name azure-cli-ml
    ```

3. Run the sample using az cli v2

    ```bash
    az ml job create --file ./pipeline.yaml -w WORKSPACE -g GROUP
    ```
