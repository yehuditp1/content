import demistomock as demisto
from CommonServerPython import *  # noqa # pylint: disable=unused-wildcard-import
from CommonServerUserPython import *  # noqa

import requests
from typing import Dict

# Disable insecure warnings
requests.packages.urllib3.disable_warnings()  # pylint: disable=no-member

''' CONSTANTS '''

DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'  # ISO8601 format with UTC, default in XSOAR

MAX_ENTRIES = 100
TIMEOUT = 30
''' CLIENT CLASS '''


class Client(BaseClient):
    @logger
    def __init__(self, app_id: str, verify: bool, proxy: bool):
        client_args = {
            'self_deployed': True,  # We always set the self_deployed key as True because when not using a self
            # deployed machine, the DEVICE_CODE flow should behave somewhat like a self deployed
            # flow and most of the same arguments should be set, as we're !not! using OProxy.
            'auth_id': app_id,
            'token_retrieval_url': 'https://login.windows.net/organizations/oauth2/v2.0/token',
            'grant_type': DEVICE_CODE,
            'base_url': 'https://api.security.microsoft.com',
            'verify': verify,
            'proxy': proxy,
            'scope': 'offline_access https://security.microsoft.com/mtp/.default',
            'ok_codes': (200, 201, 202, 204),
            'resource': 'https://api.security.microsoft.com'
        }
        self.ms_client = MicrosoftClient(**client_args)  # type: ignore

    @logger
    def incidents_list(self, limit: int = MAX_ENTRIES, status: Optional[str] = None, assigned_to: Optional[str] = None,
                       timeout: int = TIMEOUT, from_date: Optional[datetime] = None,
                       skip: Optional[int] = None) -> Dict:
        """
        GET request from the client using OData operators:
            - $top: how many incidents to receive, maximum value is 100
            - $filter: OData query to filter the the list on the properties:
                                                                lastUpdateTime, createdTime, status, and assignedTo
        Args:
            limit (int): how many incidents to receive, the maximum value is 100
            status (str): filter list to contain only incidents with the given status (Active, Resolved, or Redirected)
            assigned_to (str): Owner of the incident, or None if no owner is assigned
            timeout (int): The amount of time (in seconds) that a request will wait for a client to
                establish a connection to a remote machine before a timeout occurs.
            from_date (datetime): get incident with creation date more recent than from_date
            skip (int): how many entries to skip

        Returns: request results as dict:
                    { '@odata.context',
                      'value': list of incidents,
                      '@odata.nextLink'
                    }

        """
        params = {'$top': limit}
        filter_query = ''
        if status:
            filter_query += 'status eq ' + "'" + status + "'"

        if assigned_to:
            filter_query += ' and ' if filter_query else ''
            filter_query += 'assignedTo eq ' + assigned_to

        # fetch incidents
        if from_date:
            filter_query += ' and ' if filter_query else ''
            filter_query += f"createdTime gt {from_date}"

        if filter_query:
            params['$filter'] = filter_query  # type: ignore

        if skip:
            params['$skip'] = skip

        return self.ms_client.http_request(method='GET', url_suffix='api/incidents', timeout=timeout,
                                           params=params)

    @logger
    def update_incident(self, incident_id: int, status: Optional[str], assigned_to: Optional[str],
                        classification: Optional[str],
                        determination: Optional[str], tags: Optional[List[str]], timeout: int = TIMEOUT) -> Dict:
        """
        PATCH request to update single incident.
        Args:
            incident_id: incident's id
            status: Specifies the current status of the alert. Possible values are: (Active, Resolved or Redirected)
            assigned_to: Owner of the incident.
            classification: Specification of the alert. Possible values are: Unknown, FalsePositive, TruePositive.
            determination:  Specifies the determination of the alert. Possible values are: NotAvailable, Apt,
                                 Malware, SecurityPersonnel, SecurityTesting, UnwantedSoftware, Other.
            tags: Custom tags associated with an incident. Separated by commas without spaces (CSV)
                 for example: tag1,tag2,tag3.
            timeout: The amount of time (in seconds) that a request will wait for a client to
                establish a connection to a remote machine before a timeout occurs.
       Returns: request results as dict:
                    { '@odata.context',
                      'value': updated incident,
                    }

        """
        body = assign_params(status=status, assignedTo=assigned_to, classification=classification,
                             determination=determination, tags=tags)
        updated_incident = self.ms_client.http_request(method='PATCH', url_suffix=f'api/incidents/{incident_id}',
                                                       json_data=body, timeout=timeout)
        return updated_incident

    @logger
    def advanced_hunting(self, query: str, timeout: int = TIMEOUT):
        """
        POST request to the advanced hunting API:
        Args:
            query: query advanced hunting query language
            timeout: The amount of time (in seconds) that a request will wait for a client to
                     establish a connection to a remote machine before a timeout occurs.

        Returns:
            The response object contains three top-level properties:

                Stats - A dictionary of query performance statistics.
                Schema - The schema of the response, a list of Name-Type pairs for each column.
                Results - A list of advanced hunting events.
        """
        return self.ms_client.http_request(method='POST', url_suffix='api/advancedhunting/run',
                                           json_data={"Query": query}, timeout=timeout)


@logger
def start_auth(client: Client) -> CommandResults:
    result = client.ms_client.start_auth('!microsoft-365-defender-auth-complete')
    return CommandResults(readable_output=result)


@logger
def complete_auth(client: Client) -> CommandResults:
    client.ms_client.get_access_token()
    return CommandResults(readable_output='✅ Authorization completed successfully.')


@logger
def reset_auth() -> CommandResults:
    set_integration_context({})
    return CommandResults(readable_output='Authorization was reset successfully. You can now run '
                                          '**!microsoft-365-defender-auth-start** and **!microsoft-365-defender-auth-complete**.')


@logger
def test_connection(client: Client) -> CommandResults:
    test_context_for_token()
    client.ms_client.get_access_token()  # If fails, MicrosoftApiModule returns an error
    return CommandResults(readable_output='✅ Success!')


''' HELPER FUNCTIONS '''


def test_context_for_token() -> None:
    """test_context_for_token
    Checks if the user acquired token via the authentication process.
    Args:
    Returns:

    """
    if not get_integration_context().get('access_token'):
        raise DemistoException(
            "This integration does not have a test module. Please run !microsoft-365-defender-auth-start and "
            "!microsoft-365-defender-auth-complete and check the connection using !microsoft-365-defender-auth-test")


def test_module(client: Client) -> str:
    """Tests API connectivity and authentication'

    Returning 'ok' indicates that the integration works like it is supposed to.
    Connection to the service is successful.
    Raises exceptions if something goes wrong.

    :type client: ``Client``
    :param Client: client to use

    :return: 'ok' if test passed.
    :rtype: ``str``
    """
    # This  should validate all the inputs given in the integration configuration panel,
    # either manually or by using an API that uses them.

    test_connection(client)

    return "ok"


def convert_incident_to_readable(raw_incident: Dict) -> Dict:
    """
    Converts incident received from microsoft 365 defender to readable format
    Args:
        raw_incident: The incident as received from microsoft 365 defender

    Returns: new dictionary with keys mapping.

    """
    if not raw_incident:
        raw_incident = {}
    alerts_list = raw_incident.get('alerts', [])

    alerts_status = [alert.get('status') for alert in alerts_list]
    return {
        'Incident name': raw_incident.get('incidentName'),
        'Tags': ', '.join(raw_incident.get('tags', [])),
        'Severity': raw_incident.get('severity'),
        'Incident ID': raw_incident.get('incidentId'),
        # investigation state - relevant only for alerts.
        'Categories': ', '.join({alert.get('category') for alert in alerts_list}),
        'Impacted entities': ', '.join({entity.get('accountName') for alert in alerts_list
                                        for entity in alert.get('entities') if entity.get('entityType') == 'User'}),
        'Active alerts': f'{alerts_status.count("Active")} / {len(alerts_status)}',
        'Service sources': ', '.join({alert.get('serviceSource') for alert in alerts_list}),
        'Detection sources': ', '.join({alert.get('detectionSource') for alert in alerts_list}),
        # Data sensitivity - is not relevant
        'First activity': alerts_list[0].get('firstActivity') if alerts_list else '',
        'Last activity': alerts_list[-1].get('lastActivity') if alerts_list else '',
        'Status': raw_incident.get('status'),
        'Assigned to': raw_incident.get('assignedTo', 'Unassigned'),
        'Classification': raw_incident.get('classification', 'Not set'),
        'Device groups': ', '.join({device.get('deviceDnsName') for alert in alerts_list
                                    for device in alert.get('devices')})
    }


''' COMMAND FUNCTIONS '''


@logger
def microsoft_365_defender_incidents_list_command(client: Client, args: Dict) -> CommandResults:
    """
    Returns list of the latest incidents in microsoft 365 defender in readable table.
    The list can be filtered using the following arguments:
        - limit - number of incidents in the list, integer between 0 to 100.
        - status - fetch only incidents with the given status.
    Args:
        client(Client): Microsoft 365 Defender's client to preform the API calls.
        args(Dict): Demisto arguments:
              - limit - integer between 0 to 100
              - status - get incidents with the given status (Active, Resolved or Redirected)
              - assigned_to - get incidents assigned to the given user
              - offset - skip the first N entries of the list
    Returns: CommandResults

    """
    limit = arg_to_number(args.get('limit', MAX_ENTRIES), arg_name='limit', required=True)
    status = args.get('status')
    assigned_to = args.get('assigned_to')
    offset = arg_to_number(args.get('offset'))

    response = client.incidents_list(limit=limit, status=status, assigned_to=assigned_to, skip=offset)
    
    raw_incidents = response.get('value')
    readable_incidents = [convert_incident_to_readable(incident) for incident in raw_incidents]
    # the table headers are the incident keys. creates dummy incident to manage a situation of empty list.
    headers = list(convert_incident_to_readable({}).keys())
    human_readable_table = tableToMarkdown(name="Incidents:", t=readable_incidents, headers=headers)

    return CommandResults(outputs_prefix='Microsoft365Defender.Incident', outputs_key_field='incidentId',
                          outputs=raw_incidents, readable_output=human_readable_table)


@logger
def microsoft_365_defender_incident_update_command(client: Client, args: Dict) -> CommandResults:
    """
    Update an incident.
    Args:
        client(Client): Microsoft 365 Defender's client to preform the API calls.
        args(Dict): Demisto arguments:
              - id - incident's id (required)
              - status - Specifies the current status of the alert. Possible values are: (Active, Resolved or Redirected)
              - assigned_to - Owner of the incident.
              - classification - Specification of the alert. Possible values are: Unknown, FalsePositive, TruePositive.
              - determination -  Specifies the determination of the alert. Possible values are: NotAvailable, Apt,
                                 Malware, SecurityPersonnel, SecurityTesting, UnwantedSoftware, Other.
              - tags - Custom tags associated with an incident. Separated by commas without spaces (CSV)
                       for example: tag1,tag2,tag3.

    Returns: CommandResults
    """
    raw_tags = args.get('tags')
    tags = raw_tags.split(',') if raw_tags else None
    status = args.get('status')
    assigned_to = args.get('assigned_to')
    classification = args.get('classification')
    determination = args.get('determination')
    incident_id = arg_to_number(args.get('id'))

    updated_incident = client.update_incident(incident_id=incident_id, status=status, assigned_to=assigned_to,
                                              classification=classification,
                                              determination=determination, tags=tags)
    if updated_incident.get('@odata.context'):
        del updated_incident['@odata.context']

    readable_incident = convert_incident_to_readable(updated_incident)
    human_readable_table = tableToMarkdown(name=f"Updated incident No. {incident_id}:", t=readable_incident,
                                           headers=list(readable_incident.keys()))

    return CommandResults(outputs_prefix='Microsoft365Defender.Incident', outputs_key_field='incidentId',
                          outputs=updated_incident, readable_output=human_readable_table)


@logger
def fetch_incidents(client: Client, first_fetch_time: str, fetch_limit: int) -> List[Dict]:
    """
    Uses to fetch incidents into Demisto
    Documentation: https://xsoar.pan.dev/docs/integrations/fetching-incidents#the-fetch-incidents-command

    Due to API limitations (The incidents are not ordered and there is a limit of 100 incident for each request),
    We get all the incidents newer than last_run/first_fetch_time and saves them in a queue. The queue is sorted by
    creation date of each incident.

    As long as the queue has more incidents than fetch_limit the function will return the oldest incidents in the queue.
    If the queue is smaller than fetch_limit we fetch more incidents with the same logic described above.


    Args:
        client(Client): Microsoft 365 Defender's client to preform the API calls.
        first_fetch_time(str): From when to fetch if first time, e.g. `3 days`.
        fetch_limit(int): The number of incidents in each fetch.

    Returns:
        incidents, new last_run
    """

    test_context_for_token()

    last_run_dict = demisto.getLastRun()

    last_run = last_run_dict.get('last_run')
    if not last_run:  # this is the first run
        last_run = dateparser.parse(first_fetch_time).strftime(DATE_FORMAT)

    # creates incidents queue
    incidents_queue = last_run_dict.get('incidents_queue', [])

    if len(incidents_queue) < fetch_limit:
        # The API is limited to MAX_ENTRIES incidents for each requests, if we are trying to get more than MAX_ENTRIES
        # incident we skip the number of incidents we already fetched.

        skip = 0
        incidents = list()
        while True:  # as long as there are incidents to fetch run this loop.
            response = client.incidents_list(from_date=last_run, skip=skip)
            raw_incidents = response.get('value')
            incidents += [{
                "name": f"Microsoft 365 Defender {incident.get('incidentId')}",
                "occurred": incident.get('createdTime'),
                "rawJSON": json.dumps(incident)
            } for incident in raw_incidents]

            # raw_incidents length is less than MAX_ENTRIES than we fetch all the relevant incidents
            if len(raw_incidents) < int(MAX_ENTRIES):
                break
            skip += int(MAX_ENTRIES)

        incidents.sort(key=lambda x: dateparser.parse(x['occurred']))  # sort the incidents by the creation time
        incidents_queue += incidents

    oldest_incidents = incidents_queue[:fetch_limit]
    new_last_run = incidents_queue[-1]["occurred"] if oldest_incidents else last_run  # newest incident creation time
    demisto.setLastRun({'last_run': new_last_run,
                        'incidents_queue': incidents_queue[fetch_limit:]})
    return oldest_incidents


@logger
def microsoft_365_defender_advanced_hunting_command(client: Client, args: Dict) -> CommandResults:
    """
    Sends a query for the advanced hunting tool.
    Args:
        client(Client): Microsoft 365 Defender's client to preform the API calls.
        args(Dict): Demisto arguments:
              - query - The query to run (required)

    Returns:

    """
    query = args.get('query')

    response = client.advanced_hunting(query)
    
    results = response.get('Results')
    schema = response.get('Schema', {})
    headers = [item.get('Name') for item in schema]
    context_result = {'query': query, 'results': results}
    human_readable_table = tableToMarkdown(name=f" Result of query: {query}:", t=results,
                                           headers=headers)
    return CommandResults(outputs_prefix='Microsoft365Defender.Hunt', outputs_key_field='query', outputs=context_result,
                          readable_output=human_readable_table)


''' MAIN FUNCTION '''


def main() -> None:
    """main function, parses params and runs command functions

    :return:
    :rtype:
    """

    # if your Client class inherits from BaseClient, SSL verification is
    # handled out of the box by it, just pass ``verify_certificate`` to
    # the Client constructor
    verify_certificate = not demisto.params().get('insecure', False)

    # if your Client class inherits from BaseClient, system proxy is handled
    # out of the box by it, just pass ``proxy`` to the Client constructor
    proxy = demisto.params().get('proxy', False)
    app_id = demisto.params().get('app_id')
    first_fetch_time = demisto.params().get('first_fetch', '3 days').strip()
    fetch_limit = demisto.params().get('max_fetch', 10)
    demisto.debug(f'Command being called is {demisto.command()}')

    command = demisto.command()
    args = demisto.args()

    try:
        client = Client(
            app_id=app_id,
            verify=verify_certificate,
            proxy=proxy)

        if demisto.command() == 'test-module':
            # This is the call made when pressing the integration Test button.
            return_results(test_module(client))

        elif command == 'microsoft-365-defender-auth-start':
            return_results(start_auth(client))

        elif command == 'microsoft-365-defender-auth-complete':
            return_results(complete_auth(client))

        elif command == 'microsoft-365-defender-auth-reset':
            return_results(reset_auth())

        elif command == 'microsoft-365-defender-auth-test':
            return_results(test_connection(client))

        elif command == 'microsoft-365-defender-incidents-list':
            return_results(microsoft_365_defender_incidents_list_command(client, args))

        elif command == 'microsoft-365-defender-incident-update':
            return_results(microsoft_365_defender_incident_update_command(client, args))

        elif command == 'microsoft-365-defender-advanced-hunting':
            return_results(microsoft_365_defender_advanced_hunting_command(client, args))

        elif command == 'fetch-incidents':
            fetch_limit = arg_to_number(fetch_limit)
            incidents = fetch_incidents(client, first_fetch_time, fetch_limit)
            demisto.incidents(incidents)
        else:
            raise NotImplementedError
    # Log exceptions and return errors
    except Exception as e:
        demisto.error(traceback.format_exc())  # print the traceback
        return_error(f'Failed to execute {demisto.command()} command.\nError:\n{str(e)}')


from MicrosoftApiModule import *  # noqa: E402

''' ENTRY POINT '''

if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
