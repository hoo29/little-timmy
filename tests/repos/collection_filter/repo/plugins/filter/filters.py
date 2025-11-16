class FilterModule(object):

    def filters(self):
        return {
            "k8s_daemonset_healthy": self.k8s_daemonset_healthy
        }

    def k8s_daemonset_healthy(self, a, b):
        return True
