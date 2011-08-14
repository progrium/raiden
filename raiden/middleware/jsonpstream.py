""" Middleware for HttpStreamGateway for JSONP streaming

This makes HttpStreamGateway support JSONP streaming (infinite iframe). It's a 
proof of concept pulled from the design in Realtime, but since it's not used in
production anymore, it's not fully support here yet. It's best as just an 
example of something you can do in Raiden.

Keep in mind it was made for crossdomain infinite iframe, so it's a little more
complicated that it might seem like it should be.

"""
from cgi import parse_qs

class JsonpStreamMiddleware(object):
    def __init__(self, app, onmessage_param='_m', onconnect_param='_c', proxy_param='_p'):
        self.app = app
        self.onmessage_param = onmessage_param
        self.onconnect_param = onconnect_param
        self.proxy_param = proxy_param
        # TODO: more
    
    def __call__(self, env, start_response):
        params = parse_qs(env.get('QUERY_STRING', ''))
        if self.onmessage_param in params:
            preamble = _preamble % dict(
                proxy=params.get(self.proxy_param, [None])[0],
                jsonp_onmessage=params.get(self.onmessage_param, [None])[0],
                jsonp_onconnect=params.get(self.onconnect_param, [None])[0],)
            pass # TODO: more


_preamble = """<html><head>
    <title></title>
    </head><body></body>
    <script type="text/javascript">
    /* json2.js 
     * 2008-01-17
     * Public Domain
     * No warranty expressed or implied. Use at your own risk.
     * See http://www.JSON.org/js.html
    */
    if(!this.JSON){JSON=function(){function f(n){return n<10?'0'+n:n;}
    Date.prototype.toJSON=function(){return this.getUTCFullYear()+'-'+
    f(this.getUTCMonth()+1)+'-'+
    f(this.getUTCDate())+'T'+
    f(this.getUTCHours())+':'+
    f(this.getUTCMinutes())+':'+
    f(this.getUTCSeconds())+'Z';};var m={'\b':'\\b','\t':'\\t','\n':'\\n','\f':'\\f','\r':'\\r','"':'\\"','\\':'\\\\'};function stringify(value,whitelist){var a,i,k,l,r=/["\\\x00-\x1f\x7f-\x9f]/g,v;switch(typeof value){case'string':return r.test(value)?'"'+value.replace(r,function(a){var c=m[a];if(c){return c;}
    c=a.charCodeAt();return'\\u00'+Math.floor(c/16).toString(16)+
    (c%16).toString(16);})+'"':'"'+value+'"';case'number':return isFinite(value)?String(value):'null';case'boolean':case'null':return String(value);case'object':if(!value){return'null';}
    if(typeof value.toJSON==='function'){return stringify(value.toJSON());}
    a=[];if(typeof value.length==='number'&&!(value.propertyIsEnumerable('length'))){l=value.length;for(i=0;i<l;i+=1){a.push(stringify(value[i],whitelist)||'null');}
    return'['+a.join(',')+']';}
    if(whitelist){l=whitelist.length;for(i=0;i<l;i+=1){k=whitelist[i];if(typeof k==='string'){v=stringify(value[k],whitelist);if(v){a.push(stringify(k)+':'+v);}}}}else{for(k in value){if(typeof k==='string'){v=stringify(value[k],whitelist);if(v){a.push(stringify(k)+':'+v);}}}}
    return'{'+a.join(',')+'}';}}
    return{stringify:stringify,parse:function(text,filter){var j;function walk(k,v){var i,n;if(v&&typeof v==='object'){for(i in v){if(Object.prototype.hasOwnProperty.apply(v,[i])){n=walk(i,v[i]);if(n!==undefined){v[i]=n;}}}}
    return filter(k,v);}
    if(/^[\],:{}\s]*$/.test(text.replace(/\\./g,'@').replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g,']').replace(/(?:^|:|,)(?:\s*\[)+/g,''))){j=eval('('+text+')');return typeof filter==='function'?walk('',j):j;}
    throw new SyntaxError('parseJSON');}};}();}
    
    /**
     * The CrossFrame singleton allows iframes to safely communicate even
     * if they are on different domains. This utility requires a proxy HTML
     * file (proxy.html)
     *
     * Author: Julien Lecomte <jlecomte@yahoo-inc.com>
     * Modified by: Jeff Lindsay <jeff.lindsay@twilio.com>
     * Copyright (c) 2007, Yahoo! Inc. All rights reserved.
     * Code licensed under the BSD License:
     *     http://developer.yahoo.net/yui/license.txt
     *
     * @class CrossFrame
     */
    CrossFrame = (function () {

        var r1 = /^(((top|parent|frames\[((['"][a-zA-Z\d-_]*['"])|\d+)\]))(\.|$))+/;
        var r2 = /top|parent|frames\[(?:(?:['"][a-zA-Z]*['"])|\d+)\]/;

        function parseQueryString(s) {

            var r, a, p;

            r = {};
            a = s.split('&');
            for (i = 0; i < a.length; i++) {
                p = a[i].split('=');
                if (p.length === 2 && p[0].length > 0) {
                    r[p[0]] = unescape(p[1]);
                }
            }

            return r;
        }

        // This function is copied from yahoo.js.
        // This keeps this file free of dependencies.
        function hasOwnProperty(o, prop) {

            if (Object.prototype.hasOwnProperty) {
                return o.hasOwnProperty(prop);
            }

            return typeof o[prop] !== "undefined" &&
                    o.constructor.prototype[prop] !== o[prop];
        }

        if (window.opera) {

            // Opera does not allow reading any property (including parent, frames)
            // if the domain of the caller and the domain of the target window do
            // not match. We work around this by chaining calls, and using Opera's
            // postMessage function...
            document.addEventListener("message", function (evt) {
                var o = parseQueryString(evt.data);
                if (hasOwnProperty(o, "target") &&
                        hasOwnProperty(o, "message") &&
                        hasOwnProperty(o, "callback")) {
                    if (o.target.length > 0) {
                        // Send the message to the next document in the chain.
                        CrossFrame.send(null, o.target, o.callback, o.message);
                    } else {
                        // Let the application know a message has been received.
                        c = eval(o.callback);
                        c(o.message);
                    }
                }
            }, false);

        }

        return {

            /**
             * Sends a message to an iframe, using the specified proxy.
             *
             * @method send
             * @param {string} proxy Complete path to the proxy file.
             * @param {string} target Target iframe e.g: parent.frames["foo"]
             * @param {string} message The message to send.
             */
            send: function (proxy, target, callback, message) {

                var m, t, d, u, s, el;

                // Match things like parent.frames["aaa"].top.frames[0].frames['bbb']
                if (!r1.test(target)) {
                    throw new Error("Invalid target: " + target);
                }

                // TODO modern operas work differently. investigate.
                if (false) {

                    // Opera is the only A-grade browser that does not allow
                    // reading properties like parent.frames when this document and
                    // its parent are on separate domains. The solution is to use
                    // the parent as a "hub" to route messages to the appropriate
                    // IFrame, and use the Opera's postMessage function...

                    m = r2.exec(target);
                    // safe to eval...
                    t = eval(m[0]).document;

                    // Remove one element from the target chain.
                    target = target.substr(m[0].length + 1);

                    // Compose the message...
                    //d = arguments.length > 3 ? arguments[3] : document.domain;
                    //u = arguments.length > 4 ? arguments[4] : location.href;
                    s = "target=" + escape(target) +
                        "&message=" + escape(message) +
                        "&callback=" + escape(callback);

                    // ...and send it!
                    t.postMessage(s);

                } else {

                    // Create a new hidden iframe.
                    el = document.createElement("iframe");
                    el.style.position = "absolute";
                    el.style.visibility = "hidden";
                    el.style.top = el.style.left = "0";
                    el.style.width = el.style.height = "0";
                    document.body.appendChild(el);

                    // Listen for the onload event.
                    if ("addEventListener" in el) {
                        var cleanup = function (evt) {
                            evt.returnValue = false;
                            // First, remove the event listener or the iframe
                            // we intend to discard will not be freed...
                            evt.srcElement.detachEvent("load", cleanup);
                            // Discard the iframe...
                            setTimeout(function () {
                                document.body.removeChild(el);
                            }, 1000);
                        };
                        el.addEventListener("load", cleanup, false);
                    } else if ("attachEvent" in el) {
                        var cleanup = function (evt) {
                            evt.returnValue = false;
                            evt.srcElement.detachEvent("load", cleanup);
                            setTimeout(function () {
                                document.body.removeChild(el);
                            }, 1000);
                        };
                        el.attachEvent("load", cleanup);
                    }

                    // Compose the message...
                    s = "target=" + escape(target) +
                        "&callback=" + escape(callback) + 
                        "&message=" + escape(message);

                    // Set its src first...
                    el.src = proxy + "#" + s;

                    // ...and then append it to the body of the document.
                    //document.body.appendChild(el);
                }
            }
        };

    })();
    var defaultProxy = document.referrer.split('/').slice(0,-1).concat(['proxy.html']).join('/');
    var proxy = "%(proxy)s" || defaultProxy;
    function message(obj) {
        CrossFrame.send(proxy, "parent", "%(jsonp_onmessage)s", JSON.stringify(obj));
    }
    var x = document.domain.split('.');
    document.domain = x.slice(-2, x.length).join(".");
    try { 
      CrossFrame.send(proxy, "parent", "%(jsonp_onconnect)s", "{}"); 
    } catch (e) {
      if ("console" in window) console.error(e);
    }
    </script>
"""