class JMXParser(object):
    def __init__(self,jmx):
        self.jmx = jmx
        self.mapping = {'timestamp': ['timeStamp'],
                        'time': ['elapsed'],
                        'label': ['label'],
                        'code': ['responseCode'],
                        'message': ['responseMessage'],
                        'threadName': ['threadName'],
                        'dataType': ['dataType'],
                        'success': ['success'],
                        'saveAssertionResultsFailureMessage': ['failureMessage'],
                        'bytes': ['bytes'],
                        'threadCounts': ['grpThreads', 'allThreads'],
                        'url': ['URL'],
                        'fileName': ['Filename'],
                        'latency': ['Latency'],
                        'encoding': ['Encoding'],
                        'sampleCount': ['SampleCount', 'ErrorCount'],
                        'hostname': ['Hostname'],
                        'idleTime': ['IdleTime'],
                        'connectTime': ['Connect']}

    def _getCols(self):
        cols = [];
        for i in self.mapping:
            if i in self.jmx.sumReport and self.jmx.sumReport[i]:
                cols+=self.mapping[i]
        return cols


    def setOutput(self,name):
        return self.jmx.setOutputFilename(name)

    def getConf(self,csv,clusterID,esIP):
        ret = r"""input{
  file{
    path => "%s"
    start_position => "beginning"
    type => "jmeteroutput"
  }
}
filter{
    if [message] =~ /^\s*$/ {
        drop { }
    }
    csv{
        add_field => {"clusterID" => "%s"}
        columns => %s
    }
    mutate{
        remove_field => [ "message" ]
    }
    if [success] == "true"{ mutate { add_field => {"successRate" => 1 }} }
    else { mutate { add_field => {"successRate" => 0 }} }
}
output{
    stdout {codec => rubydebug}
    elasticsearch{
        hosts => "%s"
    }
}
"""%(csv,clusterID,str(self._getCols()).replace("'","\""),esIP)
        return ret
