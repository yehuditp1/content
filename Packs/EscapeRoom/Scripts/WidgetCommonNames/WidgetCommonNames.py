""" Widget script for calculating "Who Broke Master" Stats

"""

import demistomock as demisto
from CommonServerPython import *

import traceback
import random


''' COMMAND FUNCTION '''


def create_bar_widget() -> BarColumnPieWidget:
    widget = BarColumnPieWidget()
    name_count_mapping = {
        'Gal': 2,
        'Bar': 4,
        'Guy': 3,
    }

    for name, count in name_count_mapping.items():
        widget.add_category(name, count)

    return widget


''' MAIN FUNCTION '''


def main():
    try:
        widget = create_bar_widget()
        return_results(widget)
    except Exception as exc:
        demisto.error(traceback.format_exc())  # print the traceback
        return_error(f'Failed to execute WidgetCommonNames. Error: {str(exc)}')


''' ENTRY POINT '''


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()