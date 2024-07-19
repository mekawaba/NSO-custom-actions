# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.application import Service
from ncs.dp import Action
import time


# ---------------
# ACTIONS EXAMPLE
# ---------------
class DoubleAction(Action):
    @Action.action
    def cb_action(self, uinfo, name, kp, input, output, trans):
        self.log.info('action name: ', name)
        self.log.info('action input.number: ', input.number)

        # Updating the output data structure will result in a response
        # being returned to the caller.
        output.result = input.number * 2

class CheckBGPAction(Action):
    @Action.action
    def cb_action(self, uinfo, name, kp, input, output, trans):
        self.log.info('action name: ', name)
        self.log.info('action input.hostname: ', input.hostname)
        self.log.info('action input.nbr-addr: ', input.nbr_addr)

        count = 0
        while count < 5:
        # check BGP status
            if self.check_bgp(trans, input.hostname, input.nbr_addr):
                msg = input.hostname+": BGP session to "+input.nbr_addr+" is Established!"
                break
            else:
                msg = input.hostname+": BGP session to "+input.nbr_addr+" is down..."
                count += 1
                time.sleep(5)
        output.result = msg
    
    def check_bgp(self, trans, dev_name, bgp_nbr_addr):
        root = ncs.maagic.get_root(trans)
        device = root.ncs__devices.device[dev_name]
        ret = False
        try:
            command = "show bgp neighbor brief"
            #self.log.info('command: ', command)
            live_input = device.live_status.cisco_ios_xr_stats__exec.any.get_input()
            live_input.args = [command]
            output = device.live_status.cisco_ios_xr_stats__exec.any(live_input)
            #self.log.info("bgp_status output: ", output)
            #self.log.info("bgp_nbr_addr: ", bgp_nbr_addr)

            # parse output
            for line in output.result.split("\n"):
                if len(line)>0:
                    # if line start with the number, the line is neighbor info
                    words = line.split(" ")
                    #self.log.info(words)
                    #self.log.info("words[0]: ", words[0])
                    if bgp_nbr_addr in words[0] and "Established" in words[-2]:
                        ret = True
                        self.log.info("BGP session to ", bgp_nbr_addr, "is Established!")

            if ret == False:
                self.log.info("BGP session to ", bgp_nbr_addr, "is down...")

        except Exception as e:
            self.log.info(dev_name, " command error: ", str(e))

        return ret
    
class PingCheckAction(Action):
    @Action.action
    def cb_action(self, uinfo, name, kp, input, output, trans):
        self.log.info('action name: ', name)
        self.log.info('action input.hostname: ', input.hostname)
        self.log.info('action input.addr: ', input.addr)

        # execute Ping
        if self.ping_Loopback(trans, input.hostname, input.addr):
            msg = input.hostname+": Ping to "+input.addr+" succeeded!"
        else:
            msg = input.hostname+": Ping to "+input.addr+" failed!"
        output.result = msg

    def ping_Loopback(self, trans, dev_name, addr):
        root = ncs.maagic.get_root(trans)
        device = root.ncs__devices.device[dev_name]
        ret = False
        try:
            command = "ping "+addr
            #self.log.info('command: ', command)
            live_input = device.live_status.cisco_ios_xr_stats__exec.any.get_input()
            live_input.args = [command]
            output = device.live_status.cisco_ios_xr_stats__exec.any(live_input)
            #self.log.info("bgp_status output: ", output)
            #self.log.info("addr: ", addr)

            # parse output
            for line in output.result.split("\n"):
                #self.log.info(line)
                if len(line)>0:
                    # if line start with the number, the line is neighbor info
                    if "!!" in line:
                        ret = True
                        self.log.info("ping from ", dev_name, " to ", addr, " succeeded!")

        except Exception as e:
            self.log.info(dev_name, " command error: ", str(e))

        return ret


class BGPConfigCheckAction(Action):
    @Action.action
    def cb_action(self, uinfo, name, kp, input, output, trans):
        self.log.info('action name: ', name)
        self.log.info('action input.hostname: ', input.hostname)
        self.log.info('action input.addr: ', input.addr)

        root = ncs.maagic.get_root(trans)
        device = root.ncs__devices.device[input.hostname]

        if "xr-" in input.hostname:
            try:
                config = device.config.cisco_ios_xr__router.bgp.bgp_no_instance['100'].neighbor[input.addr]
                res = input.hostname+": BGP neighbor "+input.addr+" config exists."
            except:
                res = "No Config"
        else:
            try:
                config = device.config.junos__configuration.protocols.bgp.group['ibgp'].neighbor[input.addr]
                res = input.hostname+": BGP neighbor "+input.addr+" config exists."
            except:
                res = "No Config"

        output.result = res

        

# ------------------------
# SERVICE CALLBACK EXAMPLE
# ------------------------
class ServiceCallbacks(Service):

    # The create() callback is invoked inside NCS FASTMAP and
    # must always exist.
    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        self.log.info('Service create(service=', service._path, ')')


    # The pre_modification() and post_modification() callbacks are optional,
    # and are invoked outside FASTMAP. pre_modification() is invoked before
    # create, update, or delete of the service, as indicated by the enum
    # ncs_service_operation op parameter. Conversely
    # post_modification() is invoked after create, update, or delete
    # of the service. These functions can be useful e.g. for
    # allocations that should be stored and existing also when the
    # service instance is removed.

    # @Service.pre_modification
    # def cb_pre_modification(self, tctx, op, kp, root, proplist):
    #     self.log.info('Service premod(service=', kp, ')')

    # @Service.post_modification
    # def cb_post_modification(self, tctx, op, kp, root, proplist):
    #     self.log.info('Service postmod(service=', kp, ')')


# ---------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# ---------------------------------------------
class Main(ncs.application.Application):
    def setup(self):
        # The application class sets up logging for us. It is accessible
        # through 'self.log' and is a ncs.log.Log instance.
        self.log.info('Main RUNNING')

        # Service callbacks require a registration for a 'service point',
        # as specified in the corresponding data model.
        #
        self.register_service('checkstatus-servicepoint', ServiceCallbacks)

        # When using actions, this is how we register them:
        #
        #self.register_action('checkstatus-action', DoubleAction)
        self.register_action('checkBGPstatus-point', CheckBGPAction)
        self.register_action('pingCheck-point', PingCheckAction)
        self.register_action('configBGPcheck-point', BGPConfigCheckAction)

        # If we registered any callback(s) above, the Application class
        # took care of creating a daemon (related to the service/action point).

        # When this setup method is finished, all registrations are
        # considered done and the application is 'started'.

    def teardown(self):
        # When the application is finished (which would happen if NCS went
        # down, packages were reloaded or some error occurred) this teardown
        # method will be called.

        self.log.info('Main FINISHED')
