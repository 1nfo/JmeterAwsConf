import xml.etree.ElementTree as ET
import json


class JMX(object):
    def __init__(self,path):
        self.path = path
        self.jmx = ET.parse(path)
        self.resCollector = self._getResCollector()
        self.sumReport = self._getSumReport()

    def _getResCollector(self):
        return self.jmx.find('.//ResultCollector[@guiclass="SummaryReport"]')

    def setOutputFilename(self,name):
        self.resCollector.find('.//stringProp[@name="filename"]').text = name
        self.jmx.write(self.path)

    def _getSumReport(self):
        def transfer(i):
            if i=="true": return True
            elif i=="false": return False
            else: return eval(i)
        children = self.resCollector.find('.//value[@class="SampleSaveConfiguration"]').getchildren()
        return {c.tag:transfer(c.text) for c in children }

    # def isSaveAsXML(self):
    #     return self.jmx.find('.//ResultCollector[@guiclass="SummaryReport"]//value[@class="SampleSaveConfiguration"]//xml').text=="true"

    # def saveXMLasTrue(self):
    #     self.jmx.find('.//ResultCollector[@guiclass="SummaryReport"]//value[@class="SampleSaveConfiguration"]//xml').text = "true"
    #     self.jmx.write(self.path)
