"""Script to update Azure DNS A record with current IP address, i.e. dynamic DNS"""
from os import environ
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from dotenv import load_dotenv

from azure_client import AzureClient

load_dotenv()


def req_ifconfig_ip() -> str:
    """Retreive current IP address as reported by ifconfig.me"""
    session = Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[503],
    )
    session.mount('http://', HTTPAdapter(max_retries=retries))
    req = session.get('http://ifconfig.me', timeout=60)
    assert req.status_code == 200, f'returned code {req.status_code}'
    return req.text


def main():
    """Main Program"""
    azure = AzureClient(
        tenant_id=environ['AZURE_TENANT_ID'],
        client_id=environ['AZURE_CLIENT_ID'],
        client_secret=environ['AZURE_CLIENT_SECRET']
    )
    current_ip_addr = azure.req_dns_get_record_ip(
        subscription_id=environ['AZURE_SUBSCRIPTION_ID'],
        resource_group=environ['AZURE_RESOURCE_GROUP'],
        zone=environ['ZONE']
    )
    actual_ip_addr = req_ifconfig_ip()
    if current_ip_addr != actual_ip_addr:
        azure.req_dns_update_record(
            subscription_id=environ['AZURE_SUBSCRIPTION_ID'],
            resource_group=environ['AZURE_RESOURCE_GROUP'],
            zone=environ['ZONE'],
            ip_addr=actual_ip_addr
        )
        print('IP Address updated')
    else:
        print('No IP address change')


if __name__ == "__main__":
    main()
