import requests, ujson, time, sys, io, unicodedata, math, time
import pyasn
from itertools import groupby
import datetime
from pprint import pprint


class TraceAtlas:
    def __init__(self):
        self.all_paths = set()
        self.as_path_file = ""
        self.apfh = None
        self.traces_fh = None

    def parse_measurement(self):

        self.traces_fh = open(sys.argv[1], "a+")
        # load the ip to asn mapping
        start_time = sys.argv[2]
        stop_time = sys.argv[3]
        initial_query = "https://atlas.ripe.net/api/v2/measurements/traceroute/?start_time__gte=" + start_time + "&stop_time__lte=" + stop_time + "&af=4&page_size=500"
        print initial_query
        response = requests.get(initial_query)
        decoded_response = response.json()

        last_ts = ""
        previous_last_ts = ""
        last_id = ""

        while 'results' in decoded_response and len(decoded_response["results"]) > 0:
            for msm_object in decoded_response['results']:
                if msm_object["description"] is None:
                    continue
                last_ts = msm_object["start_time"]
                result_url = msm_object["result"]
                last_id = msm_object["id"]
                try:
                    participant_count = msm_object["participant_count"]
                    if participant_count > 1000:
                        print "!!! %s " % result_url
                        # get the list of probes
                        probe_list_url = "https://atlas.ripe.net/api/v2/measurements/%s/?optional_fields=probes" % \
                                         msm_object["id"]
                        probe_list = requests.get(probe_list_url)
                        probe_list_decoded = probe_list.json()
                        probes = list()
                        for probe in probe_list_decoded["probes"]:
                            probes.append(str(probe["id"]))
                            if len(probes) >= 100:
                                probes_str = ','.join(probes)
                                results = requests.get("%s?probe_ids=%s" % (result_url, probes_str))
                                print "%s?probe_ids=%s" % (result_url, probes_str)
                                self.traces_fh.write("%s\n" % results.text)
                                probes = list()
                        probes_str = ','.join(probes)
                        results = requests.get("%s?probe_ids=%s" % (result_url, probes_str))
                        print "%s?probe_ids=%s" % (result_url, probes_str)
                        self.traces_fh.write("%s\n" % results.text)
                    else:
                        results = requests.get(result_url)
                        print result_url
                        self.traces_fh.write("%s\n" % results.text)


                except Exception, e:
                    print "error: " + str(e)
            if 'next' in decoded_response and decoded_response['next'] is not None:
                next_query = decoded_response['next']
                print next_query
                response = requests.get(next_query)
                decoded_response = response.json()
            else:
                if last_ts != previous_last_ts:
                    next_query = "https://atlas.ripe.net/api/v2/measurements/traceroute/?stop_time__lte=" + stop_time + "&af=4&page_size=500&id__gt=" + str(
                        last_id)
                    print next_query
                    response = requests.get(next_query)
                    decoded_response = response.json()
                    previous_last_ts = last_ts
                else:
                    break

        print "Last start time: " + str(last_ts)
        self.traces_fh.flush()
        self.traces_fh.close()


tm = TraceAtlas()
tm.parse_measurement()
print "Finished."
