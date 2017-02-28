import sys,io

class Redirector:
	def __init__(self):
		self.buff = io.StringIO()
		
	def __enter__(self):
		self.stdout = sys.stdout
		sys.stdout = self
		return self

	def __exit__(self,*arg):
		sys.stdout = self.stdout

	def write(self,stdin):
		self.stdout.write(stdin)
		self.buff.write(stdin)	

	def flush(self):
		ret =  self.buff.getvalue()
		self.buff.close()
		self.stdout.write("buffer closed!")
		self.buff=io.StringIO()
		self.stdout.write(self.buff.getvalue())
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

