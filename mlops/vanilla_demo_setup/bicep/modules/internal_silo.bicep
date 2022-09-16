targetScope = 'resourceGroup'

@description('Specifies the name of the workspace.')
param workspaceName string = 'fl-demo-aml'

@description('Specifies the location of the Azure Machine Learning workspace and dependent resources.')
param location string = resourceGroup().location

@description('Specifies the name of the workspace.')
param storageAccountName string = concat(replace('${workspaceName}','-',''),'silo${location}')

@description('Specifies the name of the container for FL demo.')
param storageContainerName string = 'fldemocontainer'

param computeClusterName string = 'cpu-cluster-${location}'
param datastoreName string = 'silo_datatore_${location}'
param uaiName string = concat(replace('${workspaceName}','-',''),'-uai-${location}')


// deploy a storage account for the silo
resource siloStorageAccount 'Microsoft.Storage/storageAccounts@2021-06-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    encryption: {
      services: {
        blob: {
          enabled: true
        }
        file: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
    supportsHttpsTrafficOnly: true
  }
}

// create a container in the storage account
resource siloStorageContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2022-05-01' = {
  name: '${siloStorageAccount.name}/default/${storageContainerName}'
  properties: {
    // defaultEncryptionScope: 'string'
    // denyEncryptionScopeOverride: bool
    // enableNfsV3AllSquash: bool
    // enableNfsV3RootSquash: bool
    // immutableStorageWithVersioning: {
    //   enabled: bool
    // }
    metadata: {}
    publicAccess: 'None'
  }
}

// deploy a user assigned identify for this silo
resource siloUserAssignedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2022-01-31-preview' = {
  name: uaiName
  location: location
  tags: {
    tagName1: 'demo'
  }
}

// var roleAssignmentsToCreate = [{
//   name: guid(siloUserAssignedIdentity.id, resourceGroup().id, 'Storage Blob Data Contributor')
//   roleDefinitionId: 'Storage Blob Data Contributor'
// }]

// // set the UAI role assignment for the silo storage account
// resource roleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = [for roleAssignmentToCreate in roleAssignmentsToCreate: {
//   name: roleAssignmentToCreate.name
//   scope: resourceGroup()
//   properties: {
//     description: 'Add Storage Blob Data Contributor role to the silo storage account'
//     principalId: siloUserAssignedIdentity.properties.principalId
//     roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleAssignmentToCreate.roleDefinitionId)
//     principalType: 'ServicePrincipal' // See https://docs.microsoft.com/azure/role-based-access-control/role-assignments-template#new-service-principal to understand why this property is included.
//   }
// }]

resource siloAzureMLDatastore 'Microsoft.MachineLearningServices/workspaces/datastores@2022-06-01-preview' = {
  name: '${workspaceName}/${datastoreName}'
  properties: {
    credentials: {
      credentialsType: 'None'
      // For remaining properties, see DatastoreCredentials objects
    }
    description: 'Silo storage account in region ${location}'
    properties: {}
    tags: {}
    datastoreType: 'AzureBlob'
    // For remaining properties, see DatastoreProperties objects
    accountName: siloStorageAccount.name
    containerName: storageContainerName
    // endpoint: 'string'
    // protocol: 'string'
    resourceGroup: resourceGroup().name
    // serviceDataAccessAuthIdentity: 'string'
    subscriptionId: subscription().subscriptionId
  }
}

resource siloAzureMLCompute 'Microsoft.MachineLearningServices/workspaces/computes@2020-09-01-preview' = {
  name: '${workspaceName}/${computeClusterName}'
  location: location
  // identity: {
  //   type: 'UserAssigned'
  //   userAssignedIdentities: {
  //     '/subscriptions/${subscription()}/resourceGroups/${resourceGroup()}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/${siloUserAssignedIdentity.name}': {
  //         // principalId: siloUserAssignedIdentity.properties.principalId
  //         // clientId: siloUserAssignedIdentity.properties.clientId
  //     }
  //   }
  // }
  properties: {
    computeType: 'AmlCompute'
    properties: {
      vmSize: 'Standard_DS3_v2'
      subnet: json('null')
      osType: 'Linux'
      scaleSettings: {
        maxNodeCount: 4
        minNodeCount: 0
        // nodeIdleTimeBeforeScaleDown: '180' //  "The NodeIdleTimeBeforeScaleDown string '180' does not conform to the W3C XML Schema Part for duration."
      }
    }
  }
}
