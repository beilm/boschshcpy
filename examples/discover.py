from zeroconf import ServiceBrowser, Zeroconf, ServiceInfo, IPVersion


class MyListener:
    def filter(self, info: ServiceInfo):
        if "Bosch SHC" in info.name:
            print(f"SHC Device found!")
            print(f"Name: {info.get_name()}")
            print(f"IP: {info.parsed_addresses(IPVersion.V4Only)}")
            for host in info.parsed_addresses(IPVersion.V4Only):
                if host.startswith("169."):
                    continue
                print(f"Found host {host}")
            server_epos = info.server.find(".local.")
            if server_epos > -1:
                print(f"server: {info.server[:server_epos]}")

        # print("Service %s added, service info: %s" % (name, info))

    def update_service(self, arg0, arg1, arg2):
        return

    def remove_service(self, zeroconf, type, name):
        print("Service %s removed" % (name,))

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        self.filter(info)


zeroconf = Zeroconf()
listener = MyListener()
browser = ServiceBrowser(zeroconf, "_http._tcp.local.", listener)
try:
    input("Press enter to exit...\n\n")
finally:
    browser.cancel()
    zeroconf.close()
