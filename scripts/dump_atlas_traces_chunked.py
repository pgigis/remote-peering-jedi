import sys
import ujson
import gzip
from urllib2 import urlopen


class TraceAtlas:
    def __init__(self):
        self.traces_fh = None

    def parse_measurement(self):

        self.traces_fh = gzip.open(sys.argv[1], "a+")
        # load the ip to asn mapping
        start_time = sys.argv[2]
        stop_time = sys.argv[3]
        allow_null_desc = False
        if len(sys.argv) > 4:
            allow_null_desc = bool(int(sys.argv[4]))  # set to 1 to allow null description, 0 not to allow it
        initial_query = "https://atlas.ripe.net/api/v2/measurements/traceroute/?start_time__gte=" + \
            start_time + "&start_time__lte=" + stop_time + "&af=4&page_size=500"
        print initial_query
        response = urlopen(initial_query).read()
        decoded_response = ujson.loads(response)
        last_ts = ""
        previous_last_ts = ""
        last_id = ""

        while 'results' in decoded_response and len(decoded_response["results"]) > 0:
            for msm_object in decoded_response['results']:
                if msm_object["description"] is None and allow_null_desc is False:
                    continue
                last_ts = msm_object["start_time"]
                result_url = msm_object["result"]
                last_id = msm_object["id"]
                try:
                    # print result_url + "?stop=" + stop_time
                    response = urlopen(result_url + "?stop=" + stop_time)
                    CHUNK = 16 * 1024
                    while True:
                        chunk = response.read(CHUNK)
                        if not chunk:
                            self.traces_fh.write("\n")
                            break
                        self.traces_fh.write(chunk)

                except Exception, e:
                    print "error: " + str(e)
            if 'next' in decoded_response and decoded_response['next'] is not None:
                next_query = decoded_response['next']
                print next_query
                response = urlopen(next_query).read()
                decoded_response = ujson.loads(response)
            else:
                if last_ts != previous_last_ts:
                    next_query = "https://atlas.ripe.net/api/v2/measurements/traceroute/?start_time__lte=" + stop_time + "&af=4&page_size=500&id__gt=" + str(
                        last_id)
                    print next_query
                    response = urlopen(next_query).read()
                    decoded_response = ujson.loads(response)
                    previous_last_ts = last_ts
                else:
                    break

        print "Last start time: " + str(last_ts)
        self.traces_fh.flush()
        self.traces_fh.close()


tm = TraceAtlas()
tm.parse_measurement()
print "Finished."
