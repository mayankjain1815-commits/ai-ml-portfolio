# DNS: The Internet's Address Book

Computers find each other by IP address, but people remember names like example.com. DNS, the Domain Name System, is the bridge between the two: it translates human-friendly domain names into the numeric addresses that packets actually need. People call it the internet's phone book, but that undersells it. DNS is a huge, distributed database spread across thousands of servers, and no single machine holds the whole list.

The translation usually starts with a resolver, a helper that your internet provider or a public service runs for you. A resolver works through a well-worn chain of caches first. Your browser keeps a small cache, your operating system keeps another, and the resolver keeps a bigger one. If any of them already knows the answer and the entry has not expired, it replies immediately. That caching is why a website you visit often opens in a blink.

On a cache miss, the resolver does real work. It asks one of the root servers, which do not know every address but do know who is in charge of each top-level domain such as .com or .org. The root server points the resolver at the correct top-level domain server for the name. That server, in turn, points to the authoritative nameserver for the specific domain, the one that holds the official record. The authoritative server returns the address, and the resolver caches it and hands it back. This hierarchy is what lets the system grow without any central list that has to be updated.

DNS stores more than plain addresses. The most common record is the A record, which maps a name to an IPv4 address, and an AAAA record does the same for the longer IPv6 addresses. A CNAME record says that one name is really an alias for another, which is useful for pointing www.example.com at the same place as example.com. Other records describe where email should go or which server is allowed to speak for the domain.

Every record carries a time to live, or TTL, that tells caches how long they may keep it before checking again. A short TTL lets a company move its website to a new address quickly, because stale copies expire fast. A long TTL reduces traffic and speeds up lookups but means changes take longer to spread. Choosing a TTL is a small trade-off between freshness and efficiency.

Requests and answers travel as compact DNS messages that are separate from the web traffic they describe. That is why a slow page can sometimes be blamed on DNS: before your browser can even open a connection, it has to turn the name into an address. The whole exchange usually takes only a few milliseconds, but it happens before every new site you visit.

You can watch this machinery yourself. The command-line tool dig asks a DNS server directly and prints the answer, the records, and the TTL, which is often the fastest way to find out whether a name is broken or simply cached oddly. If the internet is a city, DNS is the directory that turns a name into a doorstep.
