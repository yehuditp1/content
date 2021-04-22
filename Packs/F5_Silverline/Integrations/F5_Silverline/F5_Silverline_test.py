import json
import io

import pytest
from F5_Silverline import get_ip_objects_list_command, add_ip_objects_command, delete_ip_objects_command, Client


def create_client(base_url: str, verify: bool, headers: dict, proxy: bool):
    return Client(base_url=base_url, verify=verify, proxy=proxy, headers=headers)


def util_load_json(path):
    with io.open(path, mode='r', encoding='utf-8') as f:
        return json.loads(f.read())


IP_ADDRESSES_TO_ADD = [
    ({'list_type': 'denylist', 'IP': '1.2.3.4'}, "IP object with IP address: 1.2.3.4 created successfully."),
    ({'list_type': 'allowlist', 'IP': '1.2.3.4', 'note': "test"},
     "IP object with IP address: 1.2.3.4 created successfully."),
]

IP_ADDRESSES_TO_DELETE = [
    ({'list_type': 'denylist', 'object_id': '850f7418-2ac9'}, "IP object with ID: 850f7418-2ac9 deleted successfully."),
    ({'list_type': 'allowlist', 'object_id': '850f7418-2ac9', 'note': "test"},
     "IP object with ID: 850f7418-2ac9 deleted successfully."),
]

IP_OBJECT_GET_LIST = [({'list_type': 'denylist', 'object_id': ['id1']}, 'ip_object_list_by_id.json'),
                      ({'list_type': 'denylist'}, 'ip_object_list_no_id.json'),
                      ({'list_type': 'denylist', 'page_number': '1', 'page_size': '1'}, 'ip_object_list_no_id.json'),
                      ({'list_type': 'denylist', 'page_number': '1', 'page_size': '1',
                        'object_id': ['id1']}, 'ip_object_list_by_id.json')]


@pytest.mark.parametrize('args,expected_output', IP_ADDRESSES_TO_ADD)
def test_add_ip_objects_command(mocker, args, expected_output):
    mocker.patch.object(Client, "request_ip_objects")
    client = create_client(base_url='https://portal.f5silverline.com/api/v1/ip_lists', verify=False, headers={},
                           proxy=False)
    result = add_ip_objects_command(client, args)
    assert result.readable_output == expected_output


@pytest.mark.parametrize('args,expected_output', IP_ADDRESSES_TO_DELETE)
def test_delete_ip_objects_command(mocker, args, expected_output):
    mocker.patch.object(Client, "request_ip_objects")
    client = create_client(base_url='https://portal.f5silverline.com/api/v1/ip_lists', verify=False, headers={},
                           proxy=False)
    result = delete_ip_objects_command(client, args)
    assert result.readable_output == expected_output


@pytest.mark.parametrize('args, response_json', IP_OBJECT_GET_LIST)
def test_get_ip_objects_list_command(mocker, args, response_json):
    client = create_client(base_url='https://portal.f5silverline.com/api/v1/ip_lists', verify=False, headers={},
                           proxy=False)
    response = util_load_json(f"test_data/{response_json}")
    mocker.patch.object(Client, "request_ip_objects", return_value=response)
    results = get_ip_objects_list_command(client, args)

    assert results.outputs_prefix == "F5Silverline.IPObjectList"
    assert results.outputs_key_field == "id"
    assert [results.outputs[0].get('id')] == args.get('object_id', ['id1'])
    assert results.outputs[0].get('attributes') == {'ip': '1.2.3.4', 'mask': '32', 'duration': 0, 'expires_at': 'None',
                                                    'list_target': 'proxy'}
    assert results.outputs[0].get('links') == {
        'self': 'https://portal.f5silverline.com/api/v1/ip_lists/denylist/ip_objects/id1?list_target=proxy'}