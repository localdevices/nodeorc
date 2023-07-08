var mockServer = require('mockserver-client');
mockServerClient = mockServer.mockServerClient;
mockServerClient("localhost", 1080).mockAnyResponse({
    "httpRequest": {
        "method": "GET",
        "path": "/status",
    },
    "httpResponse": {
        "body": "Hello World!"
    }
//    "httpResponse": {
//        "statusCode": 302,
//        "headers": {
//            "Location": [
//                "https://www.mock-server.com"
//            ]
//        },
//        "cookies": {
//            "sessionId": "2By8LOhBmaW5nZXJwcmludCIlMDAzMW"
//        }
    }
}).then(
    function () {
        console.log("expectation created");
    },
    function (error) {
        console.log(error);
    }
);
