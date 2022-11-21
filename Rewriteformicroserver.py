import asyncio
from types import NoneType
import aiohttp
from dataclasses import dataclass, field
import json

async def twx_request(request_type: str, url: str, response_type: str = 'json', data: list = [], timeout: int = 5) -> any:
    """Process Thingworx REST requests

    Args:
        request_type (str): type of request being made
        url (str): url of REST request
        response_type (str, optional): 'json' data from REST request, or http 'status' of REST request. Defaults to 'json'.
        data (list, optional): data for POST requests. Defaults to [].
        timeout (int, optional): http timeout. Defaults to 5.

    Returns:
        any: json or status depending on 'response_type'
    """
    new_data =  []
    if data:
        new_data = data.copy()

    post_data = {}
    headers = {
        'Connection' : 'keep-alive',
        'Accept' : 'application/json',
        'Content-Type' : 'application/json'
    }

    datashape = {
        'fieldDefinitions': {
            'name': {
                'name': 'name',
                'aspects': {
                    'isPrimaryKey': True
                },
            'description': 'Property name',
            'baseType': 'STRING',
            'ordinal': 0
            },
            'time': {
                'name': 'time',
                'aspects': {},
                'description': 'time',
                'baseType': 'DATETIME',
                'ordinal': 0
            },
            'value': {
                'name': 'value',
                'aspects': {},
                'description': 'value',
                'baseType': 'VARIANT',
                'ordinal': 0
            },
            'quality': {
                'name': 'quality',
                'aspects': {},
                'description': 'quality',
                'baseType': 'STRING',
                'ordinal': 0
            }
        }
    }

    async with aiohttp.ClientSession('http://localhost:8000') as session:
        request_types = {
            'get': session.get,
            'post': session.post,
            'update_tag_values': session.post
        }

        request_type = request_type.lower()
        if request_type in request_types:
            if request_type == 'update_tag_values':
                values = {}
                values['rows'] = new_data
                values['dataShape'] = datashape
                post_data = {
                    'values': values
                }

            try:
                async with request_types[request_type](url, headers = headers, json = post_data, timeout = 5) as response:
                    response_json = await response.json(content_type=None)
                    if response_type == 'json':
                        if response.status == 200:
                            return response_json
                            
                        else:
                            return None

                    elif response_type == 'status':
                        return response.status

            except Exception as e:
                print(repr(e))

        else:
            print('Request method not defined.')

async def get_twx_connection_status() -> None:
    """Gets connection status of PC to Thingworx
    """
    url = '/Thingworx/Things/Connection_Test/Services/ConnectionTest'
    
    response = await twx_request('post', url)
    if isinstance(response, dict):
        return response

    else:
        print(response)
        print("fail")

async def main():
    response = await get_twx_connection_status()
    server_seconds = response['rows'][0]['result']
    print(server_seconds)
    

if __name__ == "__main__":
    asyncio.run(main())