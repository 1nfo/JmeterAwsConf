import sys,io

class Redirector:
	def __init__(self,buffer=io.StringIO(),pauseFunc=None):
		self.buff = buffer
		self.pauseFunc = pauseFunc
		
	def __enter__(self):
		self.stdout = sys.__stdout__
		sys.stdout = self
		return self

	def __exit__(self,*arg):
		sys.stdout = sys.__stdout__

	def write(self,output):
		for i in output:
			self.stdout.write(i)
			self.buff.write(i)
			if self.pauseFunc: self.pauseFunc()	

	def flush(self):
		ret = self.buff.getvalue()
		self.buff.seek(0)
		self.buff.truncate(0)
		return ret

## test
if __name__=="__main__":
	## test
	print("redirector start:") 
	with Redirector() as re:
		print("something")

		print("now flushing")

		re.stdout.write(re.flush())

		print("flush done")

		print("flush again")

		re.stdout.write(re.flush())

	print("redirector done") 

