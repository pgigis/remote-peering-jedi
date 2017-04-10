import random, sys, collections, time
from ujson import dumps, loads
from geopy import distance
from geopy import Point
from datetime import datetime
from ripe.atlas.cousteau import ProbeRequest
from ripe.atlas.cousteau import (
    Ping,
    AtlasCreateRequest,
    AtlasSource,
    AtlasStream,
    AtlasResultsRequest,
    AtlasRequest,
    MeasurementRequest
)

import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()


class Atlas:

    def __init__(self, key, geodata_file):
        self.ATLAS_API_KEY = key
        self.city_coordinates = self.get_city_coordinates(geodata_file)
        self.min_rtts = list()

    def on_result_response(self, *args):
        """
        Function that will be called every time we receive a new result.
        Args is a tuple, so you should use args[0] to access the real message.
        """
        result = args[0]['result']
        print result
        for reply in result:
            if "rtt" in reply:
                rtt = reply["rtt"]
                self.min_rtts.append(rtt)

    def get_measurement_results(self, measurement_id):
        url_path = "/api/v2/measurements/%s/" % measurement_id
        request = AtlasRequest(**{"url_path": url_path})
        result = collections.namedtuple('Result', 'success response')
        (is_success, response) = request.get()
        if not is_success:
            self.logger.error("Unsuccessful API request for measurement ID %s", measurement_id)
        else:
            status = response["status"]["name"]
            while status != "Stopped":
                print status
                time.sleep(60)
                request = AtlasRequest(**{"url_path": url_path})
                result = collections.namedtuple('Result', 'success response')
                (is_success, response) = request.get()
                status = response["status"]["name"]

            if status == "Stopped":
                kwargs = {
                    "msm_id": measurement_id
                }

                is_success, results = AtlasResultsRequest(**kwargs).create()

                if is_success:
                    self.parse_results(results)

        return self.min_rtts

    def parse_results(self, result):
        """
        Function that will be called every time we receive a new result.
        :param result: The result of the ping measurement encoded in JSON format
        """
        for reply in result:
            if "result" in reply:
                for packet in reply["result"]:
                    if "rtt" in packet:
                        rtt = packet["rtt"]
                        self.min_rtts.append(rtt)


    @staticmethod
    def get_city_coordinates(geodata_file):
        city_coordinates = dict()
        with open(geodata_file, "r") as fin:
            for line in fin:
                lf = line.strip().split("\t")
                if len(lf) > 0:
                    city_coordinates[lf[0]] = (lf[2], lf[1])  # long, lat
        return city_coordinates

    @staticmethod
    def select_probes(city_coordinates, target_city, target_country, target_asn, probes_count):
        candidate_probes = set()
        selected_probes = set()
        probe_asn = dict()
        location = "%s|%s" % (target_city.lower(), target_country.lower())
        if location in city_coordinates:
            print "location %s found. Coordinates: " % location
            coordinates = city_coordinates[location]
            print coordinates
            # Get the probes in the same city
            filters = {"country_code": target_country, "status": 1}
            probes = ProbeRequest(**filters)

            for probe in probes:
                if probe["asn_v4"] is not None and probe["geometry"]["type"] == "Point":
                    probe_lon = probe["geometry"]["coordinates"][0]
                    probe_lat = probe["geometry"]["coordinates"][1]
                    p1 = Point("%s %s" % (coordinates[0], coordinates[1]))
                    p2 = Point("%s %s" % (probe_lon, probe_lat))
                    result = distance.distance(p1, p2).kilometers
                    if result <= 40:
                        if probe["asn_v4"] == target_asn:
                            selected_probes.add(probe["id"])
                        else:
                            candidate_probes.add(probe["id"])

            print "Number of candidate probes %s" % len(candidate_probes)
            print "Number of selected probes %s" % len(selected_probes)
            # if we have found candidate probes
            if len(candidate_probes) > 0:
                # if we don't have enough probes in the target ASN select more probes from the same city
                if len(selected_probes) < probes_count:
                    required_probes = probes_count - len(selected_probes)
                    selected_probes |= set(random.sample(candidate_probes, required_probes))
                # if we have more probes than we need
                elif len(selected_probes) > probes_count:
                    required_probes = len(selected_probes) - probes_count
                    selected_probes = set(random.sample(selected_probes, required_probes))
        else:
            print "Location not in coordinates file"
        return selected_probes

    def ping_measurement(self, af, target_ip, description, packets_num, probes_count, probes_city, probes_country, probes_asn):
        self.min_rtts = list()
        ping = Ping(af=af, target=target_ip, description=description, packets=packets_num)
        selected_probes = self.select_probes(self.city_coordinates, probes_city, probes_country, probes_asn,  probes_count)
        if len(selected_probes) > 0:
            source = AtlasSource(
                value=','.join(str(x) for x in selected_probes),
                requested=len(selected_probes),
                type="probes"
            )

            atlas_request = AtlasCreateRequest(
                start_time=datetime.utcnow(),
                key=self.ATLAS_API_KEY,
                measurements=[ping],
                sources=[source],
                is_oneoff=True
            )

            (is_success, response) = atlas_request.create()

            measurement_id = response["measurements"][0]

            atlas_stream = AtlasStream()
            atlas_stream.connect()
            # Measurement results
            channel = "atlas_result"
            # Bind function we want to run with every result message received
            atlas_stream.bind_channel(channel, self.on_result_response)
            # Subscribe to new stream for 1001 measurement results
            stream_parameters = {"msm": measurement_id}
            atlas_stream.start_stream(stream_type="result", **stream_parameters)

            # Timeout all subscriptions after 5 secs. Leave seconds empty for no timeout.
            # Make sure you have this line after you start *all* your streams
            atlas_stream.timeout(seconds=120)
            # Shut down everything
            atlas_stream.disconnect()
        else:
            print "No probes selected for %s" % target_ip
        return  self.min_rtts, measurement_id