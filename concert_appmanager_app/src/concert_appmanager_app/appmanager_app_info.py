#
# License: BSD
#   https://raw.github.com/robotics-in-concert/rocon_qt_gui/license/LICENSE
#
##############################################################################
# Imports
##############################################################################

import copy

import rospy
import concert_msgs.msg as concert_msgs
from concert_msgs.msg import ConcertClients

##############################################################################
# Graph
##############################################################################


class AppManagerApphInfo(object):
    def __init__(self):
        '''
        Creates the polling topics necessary for updating statistics
        about the running gateway-hub network.
        '''
        self._last_update = 0
        self._gateway_namespace = None
        self._concert_conductor_name = "concert_conductor"

        #Rubbish to clear out once rocon_gateway_graph is integrated
        self._event_callback = None
        self._period_callback = None
        self.is_first_update = False

        rospy.Subscriber(concert_msgs.Strings.CONCERT_CLIENTS, ConcertClients, self.update_client_list)
        rospy.Subscriber(concert_msgs.Strings.CONCERT_CLIENT_CHANGES, ConcertClients, self._update_callback)

        self._client_info_list = {}
        self._pre_client_info_list = {}

    def _update_callback(self, data):
        if self._event_callback != None:
            self._event_callback()

    def update_client_list(self, data):
        print "[app_manager_app_info]: update_client_list"

        if self.is_first_update == False:
            if self._event_callback != None:
                self._event_callback()
            if self._period_callback != None:
                self._period_callback()

            self.is_first_update = True

        client_list = []

        for k in data.clients:
            client_list.append((k, True))
        for k in data.uninvited_clients:
            client_list.append((k, False))

        for client in client_list:
            k = client[0]
            client_name = client[0].name

            if client_name in self._client_info_list:
                self._client_info_list[client_name]["is_new"] = False
            else:
                self._client_info_list[client_name] = {}
                self._client_info_list[client_name]["is_new"] = True

            self._client_info_list[client_name]["is_check"] = True

            self._client_info_list[client_name]["is_invite"] = client[1]
            self._client_info_list[client_name]["name"] = client[0].name
            self._client_info_list[client_name]["gateway_name"] = client[0].gateway_name
            self._client_info_list[client_name]["platform_info"] = client[0].platform_info
            self._client_info_list[client_name]["client_status"] = client[0].client_status
            self._client_info_list[client_name]["app_status"] = client[0].app_status

            self._client_info_list[client_name]["is_local_client"] = client[0].is_local_client
            self._client_info_list[client_name]["status"] = client[0].status

            self._client_info_list[client_name]["conn_stats"] = client[0].conn_stats
            self._client_info_list[client_name]["gateway_available"] = client[0].conn_stats.gateway_available
            self._client_info_list[client_name]["time_since_last_seen"] = client[0].conn_stats.time_since_last_seen
            self._client_info_list[client_name]["ping_latency_min"] = client[0].conn_stats.ping_latency_min
            self._client_info_list[client_name]["ping_latency_max"] = client[0].conn_stats.ping_latency_max
            self._client_info_list[client_name]["ping_latency_avg"] = client[0].conn_stats.ping_latency_avg
            self._client_info_list[client_name]["ping_latency_mdev"] = client[0].conn_stats.ping_latency_mdev

            self._client_info_list[client_name]["network_info_available"] = client[0].conn_stats.network_info_available
            self._client_info_list[client_name]["network_type"] = client[0].conn_stats.network_type
            self._client_info_list[client_name]["wireless_bitrate"] = client[0].conn_stats.wireless_bitrate
            self._client_info_list[client_name]["wireless_link_quality"] = client[0].conn_stats.wireless_link_quality
            self._client_info_list[client_name]["wireless_signal_level"] = client[0].conn_stats.wireless_signal_level
            self._client_info_list[client_name]["wireless_noise_level"] = client[0].conn_stats.wireless_noise_level

            self._client_info_list[client_name]["apps"] = {}

            for l in client[0].apps:
                app_name = l.name
                self._client_info_list[client_name]["apps"][app_name] = {}
                self._client_info_list[client_name]["apps"][app_name]['name'] = l.name
                self._client_info_list[client_name]["apps"][app_name]['display_name'] = l.display_name
                self._client_info_list[client_name]["apps"][app_name]['description'] = l.description
                self._client_info_list[client_name]["apps"][app_name]['compatibility'] = l.compatibility
                self._client_info_list[client_name]["apps"][app_name]['status'] = l.status

            #text info
            app_context = "<html>"
            app_context += "<p>-------------------------------------------</p>"
            app_context += "<p><b>name: </b>" + client[0].name + "</p>"
            app_context += "<p><b>gateway_name: </b>" + client[0].gateway_name + "</p>"
            app_context += "<p><b>rocon_uri: </b>" + client[0].platform_info.uri + "</p>"
            app_context += "<p><b>concert_version: </b>" + client[0].platform_info.version + "</p>"
            app_context += "<p>-------------------------------------------</p>"
            app_context += "<p><b>client_status: </b>" + client[0].client_status + "</p>"
            app_context += "<p><b>app_status: </b>" + client[0].app_status + "</p>"
            for l in self._client_info_list[client_name]["apps"].values():
                app_context += "<p>-------------------------------------------</p>"
                app_context += "<p><b>app_name: </b>" + l['name'] + "</p>"
                app_context += "<p><b>app_display_name: </b>" + l['display_name'] + "</p>"
                app_context += "<p><b>app_description: </b>" + l['description'] + "</p>"
                app_context += "<p><b>app_compatibility: </b>" + l['compatibility'] + "</p>"
                app_context += "<p><b>app_status: </b>" + l['status'] + "</p>"
            app_context += "</html>"
            self._client_info_list[client_name]["app_context"] = app_context

        #new node check
        for k in self._client_info_list.keys():
            if self._client_info_list[k]["is_check"] == True:
                self._client_info_list[k]["is_check"] = False
            else:
                del self._client_info_list[k]
        #update check
        if self._compare_client_info_list():
            pass
        else:
            self._event_callback()
        self._pre_client_info_list = copy.deepcopy(self._client_info_list)
        #call period callback function
        if self._period_callback != None:
            self._period_callback()

    def _reg_event_callback(self, func):
        self._event_callback = func
        pass

    def _reg_period_callback(self, func):
        self._period_callback = func
        pass

    def _compare_client_info_list(self):
        result = True
        pre = self._pre_client_info_list
        cur = self._client_info_list
        for k in cur.values():
            client_name = k["name"]
            if not (client_name in pre):
                continue
            if pre[client_name]["client_status"] != cur[client_name]["client_status"]:
                result = False
            elif pre[client_name]["app_status"] != cur[client_name]["app_status"]:
                result = False
            elif pre[client_name]["gateway_available"] != cur[client_name]["gateway_available"]:
                result = False

        return result
        pass
