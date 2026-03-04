CREATE TABLE country
(Name VARCHAR(32) NOT NULL UNIQUE,
 Code VARCHAR(4),
 Capital VARCHAR(35),
 Province VARCHAR(32),
 Area INT CHECK (Area >= 0),
 Population INT CHECK (Population >= 0),
 CONSTRAINT CountryKey PRIMARY KEY (Code));

CREATE TABLE city
(Name VARCHAR(35),
 Country VARCHAR(4),
 Province VARCHAR(32),
 Population INT CHECK (Population >= 0),
 Longitude FLOAT CHECK ((Longitude >= -180) AND (Longitude <= 180)) ,
 Latitude FLOAT CHECK ((Latitude >= -90) AND (Latitude <= 90)) ,
 CONSTRAINT CityKey PRIMARY KEY (Name, Country, Province));

CREATE TABLE province
(Name VARCHAR(32) NOT NULL ,
 Country  VARCHAR(4) NOT NULL ,
 Population INT CHECK (Population >= 0),
 Area INT CHECK (Area >= 0),
 Capital VARCHAR(35),
 CapProv VARCHAR(32),
 CONSTRAINT PrKey PRIMARY KEY (Name, Country));

CREATE TABLE economy
(Country VARCHAR(4),
 GDP INT CHECK (GDP >= 0),
 Agriculture FLOAT,
 Service FLOAT,
 Industry FLOAT,
 Inflation FLOAT,
 CONSTRAINT EconomyKey PRIMARY KEY (Country));

CREATE TABLE population
(Country VARCHAR(4),
 Population_Growth FLOAT,
 Infant_Mortality FLOAT,
 CONSTRAINT PopKey PRIMARY KEY (Country));

CREATE TABLE politics
(Country VARCHAR(4),
 Independence DATE,
 Government VARCHAR(120),
 CONSTRAINT PoliticsKey PRIMARY KEY (Country));

CREATE TABLE language
(Country VARCHAR(4),
 Name VARCHAR(50),
 Percentage FLOAT CHECK ((Percentage > 0) AND (Percentage <= 100)),
 CONSTRAINT LanguageKey PRIMARY KEY (Name, Country));

CREATE TABLE religion
(Country VARCHAR(4),
 Name VARCHAR(50),
 Percentage FLOAT CHECK ((Percentage > 0) AND (Percentage <= 100)),
 CONSTRAINT ReligionKey PRIMARY KEY (Name, Country));

CREATE TABLE ethnic_group
(Country VARCHAR(4),
 Name VARCHAR(50),
 Percentage FLOAT CHECK ((Percentage > 0) AND (Percentage <= 100)),
 CONSTRAINT EthnicKey PRIMARY KEY (Name, Country));

CREATE TABLE continent
(Name VARCHAR(20),
 Area INT(10),
 CONSTRAINT ContinentKey PRIMARY KEY (Name));

CREATE TABLE borders
(Country1 VARCHAR(4),
 Country2 VARCHAR(4),
 Length INT CHECK (Length > 0),
 CONSTRAINT BorderKey PRIMARY KEY (Country1,Country2) );

CREATE TABLE encompasses
(Country VARCHAR(4) NOT NULL,
 Continent VARCHAR(20) NOT NULL,
 Percentage FLOAT CHECK ((Percentage > 0) AND (Percentage <= 100)),
 CONSTRAINT EncompassesKey PRIMARY KEY (Country,Continent));

CREATE TABLE organization
(Abbreviation VARCHAR(12) PRIMARY KEY,
 Name VARCHAR(80) NOT NULL,
 City VARCHAR(35) ,
 Country VARCHAR(4) , 
 Province VARCHAR(32) ,
 Established DATE,
 CONSTRAINT OrgNameUnique UNIQUE (Name));

CREATE TABLE is_member
(Country VARCHAR(4),
 Organization VARCHAR(12),
 Type VARCHAR(30) DEFAULT 'member',
 CONSTRAINT MemberKey PRIMARY KEY (Country,Organization) );

CREATE TABLE mountain
(Name VARCHAR(20),
 Height INT CHECK (Height >= 0),
 Longitude FLOAT CHECK ((Longitude >= -180) AND 
            	      (Longitude <= 180)),
 Latitude FLOAT CHECK ((Latitude >= -90) AND
             	     (Latitude <= 90)),
 CONSTRAINT MountainKey PRIMARY KEY (Name));

CREATE TABLE desert
(Name VARCHAR(25),
 Area INT,
 CONSTRAINT DesertKey PRIMARY KEY (Name));

CREATE TABLE island
(Name VARCHAR(25),
 Islands VARCHAR(25),
 Area INT CHECK ((Area >= 0) and (Area <= 2175600)) ,
 Longitude FLOAT CHECK ((Longitude >= -180) AND 
		            (Longitude <= 180)),
 Latitude FLOAT CHECK ((Latitude >= -90) AND
                       (Latitude <= 90)),
 CONSTRAINT IslandKey PRIMARY KEY (Name));

CREATE TABLE lake
(Name VARCHAR(25),
 Area INT CHECK (Area >= 0),
 CONSTRAINT LakeKey PRIMARY KEY (Name));

CREATE TABLE sea
(Name VARCHAR(25),
 Depth INT CHECK (Depth >= 0),
 CONSTRAINT SeaKey PRIMARY KEY (Name));

CREATE TABLE river
(Name VARCHAR(20),
 River VARCHAR(20),
 Lake VARCHAR(20),
 Sea VARCHAR(25),
 Length INT CHECK (Length >= 0),
 CONSTRAINT RiverKey PRIMARY KEY (Name));

CREATE TABLE geo_mountain
(Mountain VARCHAR(20) ,
 Country VARCHAR(4) ,
 Province VARCHAR(32) ,
 CONSTRAINT GMountainKey PRIMARY KEY (Province,Country,Mountain) );

CREATE TABLE geo_desert
(Desert VARCHAR(25) ,
 Country VARCHAR(4) ,
 Province VARCHAR(32) ,
 CONSTRAINT GDesertKey PRIMARY KEY (Province, Country, Desert) );

CREATE TABLE geo_island
(Island VARCHAR(25) , 
 Country VARCHAR(4) ,
 Province VARCHAR(32) ,
 CONSTRAINT GIslandKey PRIMARY KEY (Province, Country, Island) );

CREATE TABLE geo_river
(River VARCHAR(20) , 
 Country VARCHAR(4) ,
 Province VARCHAR(32) ,
 CONSTRAINT GRiverKey PRIMARY KEY (Province ,Country, River) );

CREATE TABLE geo_sea
(Sea VARCHAR(25) ,
 Country VARCHAR(4)  ,
 Province VARCHAR(32) ,
 CONSTRAINT GSeaKey PRIMARY KEY (Province, Country, Sea) );

CREATE TABLE geo_lake
(Lake VARCHAR(25) ,
 Country VARCHAR(4) ,
 Province VARCHAR(32) ,
 CONSTRAINT GLakeKey PRIMARY KEY (Province, Country, Lake) );

CREATE TABLE merges_with
(Sea1 VARCHAR(25) ,
 Sea2 VARCHAR(25) ,
 CONSTRAINT MergesWithKey PRIMARY KEY (Sea1,Sea2) );

CREATE TABLE located
(City VARCHAR(35) ,
 Province VARCHAR(32) ,
 Country VARCHAR(4) ,
 River VARCHAR(20),
 Lake VARCHAR(25),
 Sea VARCHAR(25));
