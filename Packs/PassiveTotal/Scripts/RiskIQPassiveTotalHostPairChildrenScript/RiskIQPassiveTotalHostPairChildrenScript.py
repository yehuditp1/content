from CommonServerPython import *

result = demisto.executeCommand('pt-get-host-pairs',
                                {'direction': 'children', 'query': demisto.args().get('indicator_value')}
                                )

demisto.results(result)
