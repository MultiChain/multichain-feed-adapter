MultiChain Feed Adapter
=======================

[MultiChain Enterprise](https://www.multichain.com/enterprise/) feeds are real-time event logs that make it easy to reflect the contents of a blockchain (including unconfirmed transactions) to any external database. The [MultiChain Feed Adapter](https://github.com/MultiChain/multichain-feed-adapter) is a free and open source Python tool for reading these feeds and includes support for several popular databases.

This adapter is licensed under the 3-clause BSD license, which is very liberal. You are free to fork and modify this adapter for your own purposes, including:

* Adding support for additional databases.
* Modifying the code to only write some records to the database.
* Adding logic to transform data before it is written.


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
    
7. Create the target database and note down the host and database name, as well as the user and password which has access with full privileges (including creating tables).

8. In the Linux command line, make a copy of the appropriate `example-config-*.ini` file, for example:

	`cp example-config-postgres.ini config.ini`
	
9. Use your favorite text editor to edit the `config.ini` file as follows:

* Set `chain` to the name of your blockchain.
* Set `feed` to the name of the feed you created.
* Set the other parameters as required for your database.

10. In the Linux command line, start the adapter to begin synchronizing the feed to the database:

	`python3 adapter.py config.ini daemon`
	
11.	Explore the data that was written in your database in the usual way.

12. At any time the adapter can be stopped and restarted as follows:

	`python3 adapter.py config.ini stop`

	`python3 adapter.py config.ini daemon`


MultiChain Feed APIs
====================
	
Below is a brief summary of the JSON-RPC APIs in MultiChain Enterprise relating to feeds. More detailed [API documentation](https://www.multichain.com/developers/json-rpc-api/) is available online or by typing `help <command>` in the MultiChain command line:

* `createfeed`, `deletefeed` and `listfeeds` create, delete and list the configured feeds (any number can be set up).
* `addtofeed` and `updatefeed` configure a feed's contents, set options and provide flow control.
* `pausefeed` and `resumefeed` globally pause and resume a feed, using a temporary buffer to avoid losing events.
* `getdatarefdata` and `datareftobinarycache` retrieve large pieces of data which were not written in full to a feed.
* `purgefeed` removes old feed files in order to free up disk space.


Controlling Disk Usage
======================

For maximum reliability and durability, a MultiChain feed is an append-only log, which is written to disk in consecutively numbered files. As a result, over time, a feed can use up considerable disk space. In order to reduce disk usage, the following steps can be taken:

* Call the `purgefeed` JSON-RPC API periodically to remove old feed files after they have been processed.
* Use the `maxshowndata` feed option (default value: 16K) to set the maximum size of a stream item's payload to be embedded in a feed file. The full data for any item can be obtained using the `getdatarefdata` and `datareftobinarycache` APIs, passing the `dataref` values written to the feed for each stream item.
* For advanced users only: Remove unwanted events and fields using the feed options. Run `help feed-options` in the command-line tool to see a full list.


Modifying the Adapter
=====================

To add support for a new database, make a copy of `output-usertype.py` called `output-whatever.py` (replacing `whatever` with your database name) and start modifying it. There are comments within the file which provide guidance on where to add your code for initializing the database and processing the different types of events. You can also read the code for other databases such as `output-postgres.py` to see detailed examples.

Reference your `output-whatever.py` file in an output section of the `.ini` file by setting `type = whatever`. All other parameters in the same output section are easily accessed by your code. If the `type` in the `.ini` file contains a hyphen (`-`), only the text before the hyphen determines the `output-...py` file loaded.

You can also make copies of the code for supported databases and modify it for your needs. For example, you might only need to write certain types of stream items to the database, or perform some transformation on the data before it is written.