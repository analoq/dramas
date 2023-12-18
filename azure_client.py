"""Module to interfave with Azure Services"""
from typing import BinaryIO

import requests

class AzureClient:
    """Interface for Azure services"""
    DNS_TTL = 600

    def __init__(self, tenant_id: str, client_id: str, client_secret: str,
            resource:str = 'https://management.azure.com/'):
        """Retreive Azure access token for subsequent requests"""
        url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/token'
        payload = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'resource': resource,
        }
        req = requests.post(url, data=payload, timeout=60)
        assert req.status_code == 200
        response_json = req.json()
        self.access_token = response_json['access_token']

    def req_dns_get_record_ip(
            self,
            subscription_id: str,
            resource_group: str,
            zone: str) -> str:
        """Get the first IP address from an Azure DNS A-record"""
        headers = {'Authorization': f'Bearer {self.access_token}'}
        url = f'https://management.azure.com/subscriptions/{subscription_id}' \
            f'/resourceGroups/{resource_group}/providers/Microsoft.Network/dnsZones' \
            f'/{zone}/A/@?api-version=2018-05-01'
        req = requests.get(url, headers=headers, timeout=60)
        assert req.status_code == 200
        response_json = req.json()
        assert len(response_json['properties']['ARecords']) == 1
        return response_json['properties']['ARecords'][0]['ipv4Address']

    def req_dns_update_record(
            self,
            subscription_id: str,
            resource_group: str,
            zone: str,
            ip_addr: str) -> None:
        """Update an Azure DNS A-record with the provided `ip_addr`"""
        headers = {'Authorization': f'Bearer {self.access_token}'}
        url = f'https://management.azure.com/subscriptions/{subscription_id}' \
            f'/resourceGroups/{resource_group}/providers/Microsoft.Network/dnsZones' \
            f'/{zone}/A/@?api-version=2018-05-01'
        payload = {
            'properties': {
                'ARecords': [{'ipv4Address': ip_addr}],
                'TTL': self.DNS_TTL,
            }
        }
        req = requests.put(url, headers=headers, json=payload, timeout=60)
        assert req.status_code == 200

    def req_blob_upload(
            self,
            blob_account: str,
            container: str,
            blob: str,
            data: BinaryIO) -> str:
        """Upload a blob and return its URL"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'x-ms-version': '2020-04-08',
            'x-ms-blob-type': 'BlockBlob',
        }
        url = f'https://{blob_account}.blob.core.windows.net/{container}/{blob}'
        req = requests.put(url, headers=headers, data=data, timeout=60)
        assert req.status_code == 201
        return url
