class FilterModule(object):

    def filters(self):
        return {
            'cust_filter_0': self.cust_filter_0
        }

    def cust_filter_0(self, input):
        return input + "cust_filter_0"
