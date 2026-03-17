from garminconnect.mcp.server import create_mcp_server


def test_mcp_server_creates():
    server = create_mcp_server(postgres_url="postgresql://test:test@localhost/test")
    assert server is not None
    assert server.name == "Garmin Health Data"
