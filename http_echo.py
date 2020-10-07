import sys
import os
import socket
import re
from pathlib import Path
from _thread import *
import threading

def main():
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #new IPV4 socket
	host, port = "127.0.0.1", 8888
	
	#listen on port, host for up to 99 connections
	server_socket.bind((host, port))
	server_socket.listen(99)

	#keep looping, listening for connections. make a new thread for each
	while True:
		client, address = server_socket.accept()
		start_new_thread(client_connection, (client,))

#handles sending 300-500 level responses
def send_err(sock, err):
	#empty/blank variables to be filled
	header_data = {}
	headers_json = ''
	protocol, code, rmsg = 'HTTP/1.1','',''
	response = ''
	body = ''

	if(err == 400):#400 Bad Request
		body = '<html><head></head><body><h1>Bad Request</h1></body></html>'
		header_data = {
			'Connection' : 'close',
			'Content-Type' : 'text/html; encoding=utf8',
			'Content-Length': len(body)
		}
		code, rmsg = '400', 'Bad Request'
	elif(err == 404):#404 Not Found
		body = '<html><head></head><body><h1>Not Found</h1></body></html>'
		header_data = {
			'Connection' : 'close',
			'Content-Type' : 'text/html; encoding=utf8',
			'Content-Length': len(body)
		}
		code, rmsg = '404', 'Not Found'
	elif(err == 405):#405 Method Not Allowed
		body = '<html><head></head><body><h1>Method Not Allowed</h1></body></html>'
		header_data = {
			'Connection' : 'close',
			'Allow' : 'HEAD, GET',
			'Content-Type' : 'text/html; encoding=utf8',
			'Content-Length': len(body)
		}
		code, rmsg = '405', 'Not Allowed'

	#JSONify the header data dict
	headers_json = ''.join('%s: %s\r\n' % (k, v) for k, v in header_data.items())
	response = '%s %s %s\r\n' % (protocol, code, rmsg)
	sock.send(response.encode())
	sock.send(headers_json.encode())
	sock.send('\r\n'.encode())
	sock.send(body.encode())

#handles making new connections
def client_connection(client):
	client.settimeout(9)
	
	try:
		request = str((client.recv(128)).decode())
	except:
		print('request failed')
		return
	
	msg = "<html><body></body></html>"
	code = 200 #default to OK
	http_ver = 0.0
	image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.img']
	extension = 'nothing'
	is_image = False
	
	#parse out the method, file name, and HTTP version
	request_method = request.split(' ', 1)[0]
	request_file = request.split(' ', 2)[1]
	http_ver = float((request.split(' ', 3)[2].partition("\n")[0]).split('/', 1)[1])

	#attempt to parse out a file extension
	try:
		extension = os.path.splitext(request_file)[1]
	except:
		print('Failed to parse file extension')

	#check if the request has a valid method
	if(request_method not in ['GET' , 'HEAD']):
		print('Method not allowed')
		code = 405

	#make sure request is properly formatted
	if(request_file == '/'):
		request_file = '/index.html'
	elif(re.match("^(.?)/([^/]+)$", request_file) or re.match("^(.+)/([^/]+)$", request_file)):
		request_file.strip('/')
	else:
		print('Malformed request')
		if(code == 200):
			code = 400

	#pretend the cwd is template
	cwd = os.path.dirname(os.path.abspath(__file__))
	cwd += '/template'
	request_file = cwd + request_file

	#attempt to open the file
	try:
		f = open(request_file)
	except IOError:
		print("File '%s' not found" % request_file)
		if(code == 200):
			code = 404

	#no problems. file exists and can be opened
	if(code == 200):
		header_data = {
			'Content-Type': 'text/html; encoding=utf8',
			'Content-Length': os.stat(request_file).st_size,
			'Connection': 'Keep-Alive',
			'Keep-Alive': 'timeout=9'
		}

		#check if the request was for a valid image
		if(extension in image_extensions):
			f = open(request_file, 'rb')
			header_data['Content-Type'] = 'image/jpeg'
			is_image = True
		else:
			f = open(request_file)

		#convert dict to JSONic string
		headers_json = ''.join('%s: %s\r\n' % (k, v) for k, v in header_data.items())
		protocol, code, rmsg = 'HTTP/1.1', '200', 'OK'

		#package everything up and make the browser proud
		r = '%s %s %s\r\n' % (protocol, code, rmsg)
		client.send(r.encode())
		client.send(headers_json.encode())
		client.send('\r\n'.encode())

		#get the data and send it to client. if it's an image there's no need to encode; it's already binary
		packet = f.read()
		try:
			if(is_image):
				client.send(packet)
			else:
				client.send(packet.encode())
		except:
			pass

		#non-HTTP/1.1 connections must not persist
		if(http_ver == 1.0):
			client.close()
	else:
		try:
			send_err(client, code)
		except:
			pass

if __name__ == "__main__":
	main()
