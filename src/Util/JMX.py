import xml.etree.ElementTree as ET
import json


class JMX(object):
    def __init__(self,path):
        self.sumReport = self._getSumReport(path)

    def _getSumReport(self, path):
        def transfer(i):
            if i=="true": return True
            elif i=="false": return False
            else: return eval(i)
        jmx = ET.parse(path)
        children = jmx.findall('.//ResultCollector[@guiclass="SummaryReport"]')[0].find(".//value").getchildren()
        return {c.tag:transfer(c.text) for c in children }

