http_port = 8088
backend_port = 9989

def service():
    from raiden.gateways.httpstream import HttpStreamGateway
    return HttpStreamGateway()
