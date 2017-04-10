# coding=utf-8
import radix, os, sys, re, pyasn, requests, csv


class FileEmptyError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return self.value


class Helper:

    def __init__(self, pyasn_file, ixp_interfaces_file, ixp_prefixes_file):
        self.asndb = pyasn.pyasn(pyasn_file)
        self.ixp_interface_prefixes = dict()
        self.ixp_interfaces, ixp_interface_prefixes = self.read_ixp_interfaces(ixp_interfaces_file)
        self.ixppref_tree = self.construct_ixprefix_tree(ixp_prefixes_file, ixp_interface_prefixes)

    def ip2asn(self, ip):
        asn, prefix = asndb.lookup(ip)
        return asn

    def retrieve_ixp_website_data(self):
        linx_data = "https://www.linx.net/ajax/members-by-ip-asn-csv?options=short_name|website|asn|ipv4_address|ipv6_address|site_name|port_ref|network|membership_type"
        r = requests.get(linx_data)
        cr = csv.reader(r.text.encode("utf-8").splitlines(), delimiter=',')
        headers = cr.next()

        for row in cr:
            asn = row[2]
            ip = row[3]
            self.ixp_interfaces[ip] = asn

    @staticmethod
    def construct_ixprefix_tree(ixp_prefixes_file, ixp_interface_prefixes):
        """
        Read the IXP prefixes to ASNs mapping
        :return: a radix tree with the IXP prefixes
        """
        ixppref_tree = radix.Radix()
        try:
            if os.stat(ixp_prefixes_file).st_size == 0:
                raise FileEmptyError('file is empty')
            sys.stderr.write('reading ixp pref file %s\n' % ixp_prefixes_file)
            IXPPREF = open(ixp_prefixes_file, 'r')
        except OSError as o:
            sys.stderr.write('ixp pref file error: %s\n' % o)
        except FileEmptyError as f:
            sys.stderr.write('ixp pref file error: %s\n' % f)
        except IOError as i:
            sys.stderr.write('File open failed: %s\n' % i)
        else:
            for line in IXPPREF:
                if re.match(r'#', line): continue
                fields = line.strip().split('\t')
                if len(fields) != 2: continue
                try:
                    rnode = ixppref_tree.add(fields[0])
                    ixp_names = fields[1].split(",")
                    pdb_ixp_name = ixp_names[-1]
                    he_ixp_name = ixp_names[0]
                    pch_ixp_name = ixp_names[1]
                    ixp_name = pdb_ixp_name

                    if pdb_ixp_name != "n/a":
                        ixp_name = '_'.join(pdb_ixp_name.split("_")[1:]).replace("_", " ")
                    elif he_ixp_name != "n/a":
                        ixp_name = '_'.join(he_ixp_name.split("_")[1:]).replace("_", " ")
                    elif pch_ixp_name != "n/a":
                        ixp_name = '_'.join(pch_ixp_name.split("_")[1:]).replace("_", " ")
                    if ixp_name != "n/a":
                        rnode.data["origin"] = ixp_name
                except ValueError:
                    sys.stderr.write('error adding ixp pref %s\n' % fields[1])
            IXPPREF.close()

        # Check if there exist IXP prefix derived from the IXP interfaces that isn't part of the IXP prefixes list
        # If such a prefix exists add it in the list of IXP prefixes
        for prefix in ixp_interface_prefixes:
            base_ip = prefix.split("/")[0]
            rnode = ixppref_tree.search_best(base_ip)
            if rnode is None:
                ixp_name = ixp_interface_prefixes[prefix].replace("_", " ")
                rnode = ixppref_tree.add(prefix)
                rnode.data["origin"] = ixp_name

        return ixppref_tree

    @staticmethod
    def read_ixp_interfaces(ixp_interfaces_file):
        """
        :param ixp_interfaces_file: The file that includes the IXP to ASN interfaces
        :return: a dictionary that maps IXP IPs to ASNs
        """
        ixp_interfaces = dict()
        ixp_interface_prefixes = dict()
        with open(ixp_interfaces_file, "rb") as fin:
            for line in fin:
                line = line.strip()
                if line.startswith("#"): continue
                fields = line.split("|")
                if len(fields) > 1:
                    interface = fields[0]
                    member = "%s" % fields[1]
                    ixp_interfaces[interface] = member
                    # Get the /24 prefix from the interface
                    pfx_interface = '.'.join(interface.split(".")[0:3]) + ".0/24"
                    if pfx_interface not in ixp_interface_prefixes:
                        ixp_interface_prefixes[pfx_interface] = fields[2]
        return ixp_interfaces, ixp_interface_prefixes
