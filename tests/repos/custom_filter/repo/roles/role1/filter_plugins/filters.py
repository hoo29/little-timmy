class FilterModule(object):

    def filters(self):
        return {
            'cust_filter_1': self.cust_filter_1,
            'cust_filter_2': self.cust_filter_2,
        }

    def cust_filter_1(self, input):
        return input + "cust_filter_1"

    def cust_filter_2(self, input):
        return input + "cust_filter_2"
