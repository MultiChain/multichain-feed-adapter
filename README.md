MultiChain Feed Adapter
=======================

[MultiChain Enterprise](https://www.multichain.com/enterprise/) feeds are real-time event logs that make it easy to reflect the contents of a blockchain to any external database. The MultiChain Feed Adapter is a free and open source Python tool for reading these feeds and writing to some popular databases.

You are free to modify this adapter for your own purposes, including:

* Adding support for additional databases
* Inserting logic that only writes certain records to the database
* Adding transformation logic to modify the data that is written

https://github.com/MultiChain/multichain-feed-adapter

    Copyright (c) Coin Sciences Ltd
    License: BSD 3-Clause License


System Requirements
===================

* Any modern 64-bit Linux
* MultiChain Enterprise 2.0.4 Demo/Beta 1 or later
* Python 3.x
* If using the built-in database support, one of: PostgreSQL 9.2 or later, MySQL (to come), MongoDB (to come)


Getting Started
===============

1. Make sure you are running [MultiChain Enterprise](https://www.multichain.com/enterprise/) (a free demo is available to download).

2. If you have not already created a blockchain and one or more streams on that chain, you can do so by following the [Getting Started](https://www.multichain.com/getting-started/) guide. A single node is enough to get started with feeds.

3. Open the command-line tool for your blockchain node, substituting `chain1` for the blockchain name:

	`multichain-cli chain1`

4. Create a feed on your blockchain, by running this in the command-line tool:

	`createfeed feed1`
    
5. If you want the database to reflect the contents of a stream, add it to the feed by substituting the stream name below. Any number of streams can be added and each will create a separate database table:

	`addtofeed feed1 stream1`
	`addtofeed feed1 stream2`
    
6. If you want the database to include a list of blocks, add blocks to the feed as follows:

	`addtofeed feed1 '' blocks`
    
7. Create a PostgreSQL database and note down the host and database name, as well as the user and password which has access with full privileges (including creating tables).

8. In the Linux command line, make a copy of the appropriate `example-config-*.ini` file to create your own, for example:

	`cp example-config-postgres.ini config.ini`
	
9. Use your favorite text editor to edit the `config.ini` file as follows:

* Set `chain` to the name of your blockchain.
* Set `feed` to the name of the feed you created.
* Set the other parameters as required for your database.

10. In the Linux command line, start this adapter to begin synchronizing the feed to the database:

	`python3 adapter.py config.ini daemon`
	
11.	Explore the data that was written in your database in the appropriate way.

12. At any time the adapter can be stopped and restarted as follows:

	`python3 adapter.py config.ini stop`
	`python3 adapter.py config.ini daemon`


MultiChain Feed APIs
====================
	
Below is a brief summary of the JSON-RPC APIs in MultiChain Enterprise relating to feeds. More detailed documentation is available [online](https://www.multichain.com/developers/json-rpc-api/) or by typing `help <command>` in the MultiChain command line:

* `createfeed`, `deletefeed` and `listfeeds` to create, delete and list the configured feeds (any number can be defined).
* `addtofeed` and `updatefeed` to configure feed contents, set options and for flow control.
* `pausefeed` and `resumefeed` to globally pause and resume a feed, optionally using a temporary buffer to avoid losing events.
* `getdatarefdata` and `datareftobinarycache` enable the retrieval of large pieces of data which are referenced (but not written in full) to a feed.
* `purgefeed` removes old feed files in order to free up disk space.


Controlling Disk Usage
======================

For maximum reliability and durability, a MultiChain feed is an append-only log, which is written to disk in consecutively numbered files. As a result, over time, a feed can use up considerable disk space. In order to reduce disk usage, the following steps can be taken:

* Call the `purgefeed` JSON-RPC API periodically to remove old feed files after they have been processed.
* Use the `maxshowndata` feed option (default value: 16K) to control the maximum size of stream item payload that will be embedded in a feed file. The full data for any item can still be obtained using the `getdatarefdata` and `datareftobinarycache` APIs. The `dataref` parameters required by these APIs are written to the feed for each new stream item.
* For advanced users: Remove unwanted events and fields from feeds using the feed options. Run `help feed-options` in the command-line tool to see a full list of options.


Modifying the Adapter
====================

To add support for a new database, make a copy of `output-usertype.py` called `output-whatever.py` (replacing `whatever` with your database name) and start modifying it. There are comments within the file which provide guidance on where to add your code for initializing the database and processing the different types of events. You can also read the code for other databases such as `output-postgres.py` to see a detailed example.

In the `.ini` file, you can reference your `output-whatever.py` file in an output section by setting `type = whatever`. All other parameters in the output section can be read by your code in the `initialize()` function. If the `type` in the `.ini` file contains a hyphen (`-`), only the text before the hyphen determines the `.py` file loaded.

You can also makes copies of the the existing database adapters and modify them for your needs. For example, your adapter might only need to write certain types of stream items to the database, or it might perform some transformations on the data before it is written.