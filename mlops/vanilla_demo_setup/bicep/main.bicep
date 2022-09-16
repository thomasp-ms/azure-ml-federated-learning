targetScope = 'subscription'

param demoBaseName string = 'fldemo'
param workspaceName string = '${demoBaseName}-aml'
param resourceGroupName string = '${demoBaseName}-deleteme20220916-rg'
param orchestratorLocation string = 'eastus'

param siloRegions array = ['eastus', 'westus', 'westus2']

param tags object = {
  Owner: 'AzureML Samples'
  Project: 'azure-ml-federated-learning'
  Environment: 'dev'
  Toolkit: 'bicep'
  Docs: 'https://github.com/Azure-Samples/azure-ml-federated-learning'
}

// Create resource group for the demo (cold start)
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: orchestratorLocation
  tags: tags
}

// Create Azure Machine Learning workspace for orchestrator
module workspaceDeployment './modules/azureml_workspace.bicep' = {
  name: '${demoBaseName}deployazuremlworkspace${orchestratorLocation}'
  params: {
    workspaceName: workspaceName
    location: orchestratorLocation
  }  
  scope: resourceGroup
}

// Create all vanilla silos using a provided bicep module
module siloDeployments './modules/internal_silo.bicep' = [for region in siloRegions: {
  name: '${demoBaseName}deploysilo${region}'
  params: {
    workspaceName: workspaceName
    location: region
    // all other parameters left default
  }
  scope: resourceGroup  
}]
