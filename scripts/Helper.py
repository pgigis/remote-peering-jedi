import radix, os, sys, re, pyasn


class FileEmptyError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return self.value


class Helper:

    def __init__(self, pyasn_file):
        self.asndb = pyasn.pyasn(pyasn_file)

    def ip2asn(self, ip):
        asn, prefix = asndb.lookup(ip)
        return asn

    @staticmethod
    def construct_ixprefix_tree(prefixes_file):
        ixppref_tree = radix.Radix()
        try:
            if os.stat(prefixes_file).st_size == 0:
                raise FileEmptyError('file is empty')
            sys.stderr.write('reading ixp pref file %s\n' % prefixes_file)
            IXPPREF = open(prefixes_file, 'r')
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
                except ValueError:
                    sys.stderr.write('error adding ixp pref %s\n' % fields[1])
                ixp_names = fields[1].split(",")
                for ixp in ixp_names:
                    if ixp != "n/a":
                        ixp_name = ('_'.join(ixp.split("_")[1:])).replace("_", " ")
                        rnode.data["origin"] = ixp_name
                        break
            IXPPREF.close()

        return ixppref_tree
