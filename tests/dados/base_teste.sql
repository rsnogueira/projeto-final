-- Base de teste: DDL idêntico ao de Database/SQLite/db_proj_final.db e linhas COPIADAS da base real.
-- Gerada a partir da base real em 2026-11-10. Única exceção sintética: o vínculo (3118, 35368), marcado abaixo.

CREATE TABLE APLICACAO (
	CodigoAplicacao		INTEGER NOT NULL, -- pk
	CodigoFabricante	INTEGER NOT NULL, -- fk
	CodigoTipoAplicacao	INTEGER NOT NULL, -- fk 
	FaixaAno			TEXT 	NOT NULL,
	Motorizacao			TEXT 	NOT NULL,
	Combustivel			TEXT 	NOT NULL,
	DescricaoAplicacao	TEXT 	NOT NULL,
	AnoInicioFabricacao	INTEGER NOT NULL,
	AnoFimFabricacao	INTEGER,
	PRIMARY KEY(CodigoAplicacao) ,
    FOREIGN KEY (CodigoFabricante)   REFERENCES FABRICANTE (CodigoFabricante)     	ON DELETE CASCADE,
    FOREIGN KEY (CodigoTipoAplicacao) REFERENCES TIPOAPLICACAO (CodigoTipoAplicacao) 	ON DELETE CASCADE
);
CREATE TABLE "FABRICANTE" (
	"CodigoFabricante"	INTEGER NOT NULL UNIQUE,
	"DescricaoFabricante"	TEXT NOT NULL UNIQUE,
	PRIMARY KEY("DescricaoFabricante")
);
CREATE TABLE "GRUPOPRODUTO" (
	"CodigoGrupoProduto"	INTEGER NOT NULL UNIQUE,
	"DescricaoGrupoProduto"	TEXT NOT NULL UNIQUE,
	PRIMARY KEY("CodigoGrupoProduto")
);
CREATE TABLE "PRODUTO" (
	"CodigoProduto"	INTEGER NOT NULL UNIQUE,
	"DescricaoProduto"	TEXT NOT NULL,
	"CodigoGrupoProduto"	INTEGER NOT NULL,
	"PrecoProduto"	REAL,
	"NumeroProduto"	TEXT NOT NULL,
	"NumeroProdutoPesq"	TEXT NOT NULL,
	"CodigoSimilar"	TEXT,
	"CpoAuxProd5"	TEXT,
	"QtdEmbalagem"	INTEGER,
	"CpoAuxProd25"	TEXT,
	"PCs"	TEXT,
	PRIMARY KEY("CodigoProduto")
);
CREATE TABLE PRODUTO_APLICACAO (
    CodigoProduto   INTEGER NOT NULL,
    CodigoAplicacao INTEGER NOT NULL,
    PRIMARY KEY (CodigoProduto, CodigoAplicacao),
    FOREIGN KEY (CodigoProduto)   REFERENCES PRODUTO (CodigoProduto)     ON DELETE CASCADE,
    FOREIGN KEY (CodigoAplicacao) REFERENCES APLICACAO (CodigoAplicacao) ON DELETE CASCADE
);
CREATE TABLE "TIPOAPLICACAO" (
	"CodigoTipoAplicacao"	INTEGER NOT NULL,
	"DescricaoTipoAplicacao"	TEXT NOT NULL,
	PRIMARY KEY("CodigoTipoAplicacao")
);
CREATE INDEX PRODUTO_APLICACAO_APLICACAO_I ON PRODUTO_APLICACAO (CodigoAplicacao);

INSERT INTO FABRICANTE (CodigoFabricante, DescricaoFabricante) VALUES (2, 'FIAT');
INSERT INTO FABRICANTE (CodigoFabricante, DescricaoFabricante) VALUES (3, 'FORD');
INSERT INTO FABRICANTE (CodigoFabricante, DescricaoFabricante) VALUES (73, 'NISSAN');
INSERT INTO TIPOAPLICACAO (CodigoTipoAplicacao, DescricaoTipoAplicacao) VALUES (1, 'Leves');
INSERT INTO TIPOAPLICACAO (CodigoTipoAplicacao, DescricaoTipoAplicacao) VALUES (2, 'Pesados');
INSERT INTO TIPOAPLICACAO (CodigoTipoAplicacao, DescricaoTipoAplicacao) VALUES (3, 'Utilitários');
INSERT INTO TIPOAPLICACAO (CodigoTipoAplicacao, DescricaoTipoAplicacao) VALUES (4, 'Motos');
INSERT INTO TIPOAPLICACAO (CodigoTipoAplicacao, DescricaoTipoAplicacao) VALUES (5, 'Compressor');
INSERT INTO TIPOAPLICACAO (CodigoTipoAplicacao, DescricaoTipoAplicacao) VALUES (6, 'Agrícolas');
INSERT INTO TIPOAPLICACAO (CodigoTipoAplicacao, DescricaoTipoAplicacao) VALUES (7, 'Bronze');
INSERT INTO TIPOAPLICACAO (CodigoTipoAplicacao, DescricaoTipoAplicacao) VALUES (8, 'Industrial');
INSERT INTO TIPOAPLICACAO (CodigoTipoAplicacao, DescricaoTipoAplicacao) VALUES (9, 'Ônibus');
INSERT INTO GRUPOPRODUTO (CodigoGrupoProduto, DescricaoGrupoProduto) VALUES (7, 'GUIAS DE VÁLVULA');
INSERT INTO GRUPOPRODUTO (CodigoGrupoProduto, DescricaoGrupoProduto) VALUES (16, 'ALARGADORES PARA GUIAS DE VÁLVULA');
INSERT INTO GRUPOPRODUTO (CodigoGrupoProduto, DescricaoGrupoProduto) VALUES (24, 'PISTÃO');
INSERT INTO GRUPOPRODUTO (CodigoGrupoProduto, DescricaoGrupoProduto) VALUES (39, 'BRONZINA');
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (13760, 73, 3, '2006-2008', '4.07 TCE SPRINT 2.8 12V L4 SOHC', 'DIESEL', 'FRONTIER CD SE TDI 4X4', 2006, 2008);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (13761, 73, 3, '2006-2008', '4.07 TCE SPRINT 2.8 12V L4 SOHC', 'DIESEL', 'FRONTIER CD XE TDI 4X4', 2006, 2008);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (13762, 73, 3, '2006-2008', '4.07 TCE SPRINT 2.8 12V L4 SOHC', 'DIESEL', 'FRONTIER CD SE 2.8 TDI 4X2', 2006, 2008);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (13763, 73, 3, '2006-2008', '4.07 TCE SPRINT 2.8 12V L4 SOHC', 'DIESEL', 'FRONTIER CD XE 2.8 TDI 4X2', 2006, 2008);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (13764, 73, 3, '2006-2008', '4.07 TCE SPRINT 2.8 12V L4 SOHC', 'DIESEL', 'FRONTIER CS XE 2.8 TDI 4X2', 2006, 2008);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (13823, 73, 3, '2008-2013', 'YD25ETI 2.5 16V L4 DOHC', 'DIESEL', 'FRONTIER CD SE 4X4', 2008, 2013);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (13824, 73, 3, '2008-2013', 'YD25ETI 2.5 16V L4 DOHC', 'DIESEL', 'FRONTIER CD XE 4X4', 2008, 2013);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (13979, 73, 3, '2007-2013', 'YD25ETI 2.5 16V L4 DOHC', 'DIESEL', 'FRONTIER LE', 2007, 2013);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (15365, 73, 1, '2017-2023', 'HR16DE 1.6 16V L4 DOHC', 'GASOLINA', 'KICKS S 1.6', 2017, 2023);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (15366, 73, 1, '2016-2018', 'HR16DE 1.6 16V L4 DOHC', 'GASOLINA', 'KICKS SL CVT', 2016, 2018);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (29767, 73, 1, '2011-2012', 'K4M - 1.6 L 16V DOHC L4', 'FLEX', 'LIVINA', 2011, 2012);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (31383, 73, 1, '2017-2022', 'HR16DE - 1.6L 16V DOHC L4', 'FLEX', 'KICKS', 2017, 2022);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (31393, 73, 3, '2005-...', 'M9T - 2.3L 16V DOHC L4', 'DIESEL', 'FRONTIER', 2005, '');
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (31483, 73, 1, '2011-...', 'HR16DE - 1.6L 16V DOHC L4', 'FLEX', 'KICKS / MARCH / VERSA', 2011, '');
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (32111, 73, 1, '2011-2022', 'HR16DE 1.6 L 16V DOHC L4', 'FLEX', 'KICKS RIO 2016<br>KICKS SL<br>KICKS SV LIMITED<br>KICKS S<br>KICKS SV<br>KICKS SL<br>KICKS SPECIAL EDITION<br>KICKS S DIRECT<br>KICKS UCL<br>KICKS ACTIVE (PCD) 1.6 AT<br>KICKS SENSE 1.6<br>KICKS SENSE 1.6 AT<br>KICKS ADVANCE 1.6 AT<br>KICKS EXCLUSIVE 1.6 AT<br>KICKS XPLAY<br>MARCH S<br>', 2011, 2022);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (32415, 73, 3, '2007-2012', 'YD25 SELL 2.5L 16V', 'DIESEL', 'FRONTIER/ PATHFINDER', 2007, 2012);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (32452, 73, 1, '…-2014', 'MOTOR 1.6 16V', 'GASOLINA', 'LIVINA', 2014, 2014);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (32609, 73, 3, '2013-…', 'YD25DDTI 2.5L 16V', 'DIESEL', 'FRONTIER/ PATHFINDER', 2013, 2013);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (34568, 73, 1, '2013-2016', 'CVVTCS 2.0 L 16V DOHC L4', 'FLEX', 'SENTRA', 2013, 2016);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (34569, 73, 1, '2014-2016', 'CVVTCS 2.0 L 16V DOHC L4', 'FLEX', 'SENTRA', 2014, 2016);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (34590, 73, 1, '2020--', 'HR16DE 1.6 L 16V DOHC L4', 'FLEX', 'KICKS', 2020, 2020);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (34828, 73, 2, '2005-2008', 'SPRINT EURO 3 2.8 L 12V SOHC L4', 'DIESEL', 'FRONTIER', 2005, 2008);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (35368, 73, 3, '2007-2012', 'YD25ETI 2.5 L 16V DOHC L4', 'DIESEL', 'FRONTIER', 2007, 2012);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (35369, 73, 3, '2008-2012', 'YD25ETI 2.5 L 16V DOHC L4', 'DIESEL', 'FRONTIER', 2008, 2012);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (35374, 73, 3, '2013-2016', '- 2.5 L 16V DOHC L4', 'DIESEL', 'FRONTIER', 2013, 2016);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (36311, 73, 3, '2006-2011', 'YD25DDTI / YD25ETI 2.5L 16V DOHC L4', 'DIESEL', 'FRONTIER / PATHFINDER', 2006, 2011);
INSERT INTO APLICACAO (CodigoAplicacao, CodigoFabricante, CodigoTipoAplicacao, FaixaAno, Motorizacao, Combustivel, DescricaoAplicacao, AnoInicioFabricacao, AnoFimFabricacao) VALUES (36312, 73, 3, '2012-...', 'YD25DDTI / YD25ETI 2.5L 16V DOHC L4', 'DIESEL', 'FRONTIER', 2012, '');
INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, PrecoProduto, NumeroProduto, NumeroProdutoPesq, CodigoSimilar, CpoAuxProd5, QtdEmbalagem, CpoAuxProd25, PCs) VALUES (1946, 'GUIA DE VALVULA CLIO 1.0/1.6 16V +0,05', 7, 10.13, '12.1680.931', '121680931', '1946', 'ADM/ESC', 24, '206 SOLEIL, 206 TECHN...', ' #NAC_12.1680.931 NAC121680931 GUIA DE VALVULA CLIO 1.0/1.6 16V +0,05 7700109151 NISSAN PEUGEOT RENAULT 206 SOLEIL D4D 1.0 16V L4 SOHC 206 TECHNO 206 SELECTION 206 SENSATION 206 QUICKSILVER 206 SELECTION PACK KANGOO RL KANGOO RN KANGOO RT CLIO RL/RN CLIO PRIVILEGE CLIO DYNNAMIQUE CLIO EXPRESSION TWINGO INITIALE TWINGO PACK III CLIO AUTHENTIQUE KANGOO EXPRESSION KANGOO RL EXPRESS KANGOO EXPRESS FCON SCENIC RT K4M 1.6 16V L4 DOHC SCENIC RXE SCENIC ALIZE SCENIC RT16V CLIO RL CLIO RN CLIO SI MEGANE RT MEGANE RXE MEGANE SEDAN RT SCENIC PRIVILEGE SCENIC EXPRESSION KANGOO AUTHENTIQUE SCENIC AUTHENTIQUE MEGANE HATCH FII EXPRESSION CLIO CAMPUS D4D HI-POWER 1.0 16V L4 SOHC LOGAN EXPRESSION LOGAN AUTHENTIQUE LOGAN EXPRESSION G3 CLIO EXPRESSION FLEX LOGAN AUTHENTIQUE G3 SANDERO EXPRESSION 1.0 HI-POWER SANDERO AUTHENTIQUE 1.0 HI-POWER KANGOO EXPRESS 3 PORTAS KANGOO AUTHENTIQUE HI-FLEX LIVINA S LIVINA X-GEAR LIVINA X GEAR SL LOGAN PRIVILEGE SANDERO GT LINE SANDERO STEP WAY SANDERO PRIVILEGE SANDERO EXPRESSION HI-FLEX SANDERO STEP WAY TWEED AT. SANDERO PRIVILEGE HI-TORQUE SANDERO EXPRESSION HI-TORQUE SANDERO PRIVILEGE HI-FLEX AUTO DUSTER 1.6 CLIO HI-FLEX SCENIC HI FLEX DUSTER DAKAR 1.6 SYMBOL PRIVILEGE SYMBOL EXPRESSION DUSTER OUTDOOR 1.6 OROCH DYNAMIQUE 1.6 DUSTER DYNAMIQUE 1.6 DUSTER TECH ROAD 1.6 OROCH EXPRESSION 1.6 DUSTER EXPRESSION 1.6 SCENIC PRIVILEGE-FLEX CLIO PRIVILEGE HI-FLEX CLIO EXPRESSION HI-FLEX MEGANE SEDAN EXPRESSION CLIO AUTHENTIQUE HI-FLEX MEGANE NOVO B32 RS COUPE FLUENCE EXPRESSION - TAXI SCENIC EXPRESSION HI-FLEX CLIO DYNNAMIQUE HI-FLEXFLEX GRAN TOUR DYNAMIQUE HI-FLEX MEGANE SEDAN FII EXPRESSION MEGANE SEDAN FIII DYNAMIQUE MEGANE SEDAN FIII PRIVILEGE MEGANE GRAND TOUR EXPRESSION MEGANE SEDAN FIII EXPRESSION MEGANE SEDAN FII EXPRESSION HY-FLEX MEGANE SEDAN FIII DYNAMIQUE HY-FLEX ');
INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, PrecoProduto, NumeroProduto, NumeroProdutoPesq, CodigoSimilar, CpoAuxProd5, QtdEmbalagem, CpoAuxProd25, PCs) VALUES (3118, 'GUIA DE VALVULA TEMPRA 16V BRONZE STD', 7, 14.42, '12.712.070', '12712070', '3118', 'ADM/ESC', 12, 'TEMPRA OURO 16V<br><br>Alternativa - Especia', ' #NAC_12.712.070 NAC12712070 GUIA DE VALVULA TEMPRA 16V BRONZE STD FIAT TEMPRA OURO 16V<br><br>Alternativa - Especial em bronze SEVEL 2.0 L 16V DOHC L4 ');
INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, PrecoProduto, NumeroProduto, NumeroProdutoPesq, CodigoSimilar, CpoAuxProd5, QtdEmbalagem, CpoAuxProd25, PCs) VALUES (5580, 'GUIA DE VALVULA MARCH 1.0 12V / 1.6 16V STD', 7, 11.1, '11.2501.007', '112501007', '5580', 'ADM/ESC', 24, 'VERSA 1.0, MARCH 1.0 S,...', ' #NAC_11.2501.007 NAC112501007 GUIA DE VALVULA MARCH 1.0 12V / 1.6 16V STD NISSAN VERSA 1.0 HR10 1.0 12V L3 DOHC MARCH 1.0 S VERSA 1.0 S MARCH 1.0 SV MARCH 1.0 CONFORTO KICKS S 1.6 HR16DE 1.6 16V L4 DOHC KICKS SL CVT KICKS UCL AT KICKS S 1.6 AT KICKS SL 1.6 AT KICKS SV 1.6 AT KICKS S DIRECT AT KICKS RIO 2016 1.6 AT KICKS SV LIMITED 1.6 AT KICKS SPECIAL EDITION AT KICKS SPECIAL EDITION MT ');
INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, PrecoProduto, NumeroProduto, NumeroProdutoPesq, CodigoSimilar, CpoAuxProd5, QtdEmbalagem, CpoAuxProd25, PCs) VALUES (5581, 'GUIA DE VALVULA MARCH 1.0 12V / 1.6 16V +0,05', 7, 11.1, '11.2501.907', '112501907', '5581', 'ADM/ESC', 24, 'VERSA 1.0, MARCH 1.0 S,...', ' #NAC_11.2501.907 NAC112501907 GUIA DE VALVULA MARCH 1.0 12V / 1.6 16V +0,05 NISSAN VERSA 1.0 HR10 1.0 12V L3 DOHC MARCH 1.0 S VERSA 1.0 S MARCH 1.0 SV MARCH 1.0 CONFORTO KICKS S 1.6 HR16DE 1.6 16V L4 DOHC KICKS SL CVT KICKS UCL AT KICKS S 1.6 AT KICKS SL 1.6 AT KICKS SV 1.6 AT KICKS S DIRECT AT KICKS RIO 2016 1.6 AT KICKS SV LIMITED 1.6 AT KICKS SPECIAL EDITION AT KICKS SPECIAL EDITION MT ');
INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, PrecoProduto, NumeroProduto, NumeroProdutoPesq, CodigoSimilar, CpoAuxProd5, QtdEmbalagem, CpoAuxProd25, PCs) VALUES (6238, 'PISTAO FIAT UNO 1.0 8V FIRE GAS +0,40', 24, NULL, '58.2041.470', '582041470', '6238', '', NULL, 'PALIO EX MPI, PALIO RST...', ' #NAC_58.2041.470 NAC582041470 PISTAO FIAT UNO 1.0 8V FIRE GAS +0,40 P2463 PS4798S PALIO EX MPI FIRE 1.0 8V L4 SOHC PALIO RST FIRE SIENA ELX FIRE SIENA RST FIRE PALIO EX RST II PALIO YOUNG FIRE UNO MILLE EX FIRE UNO MILLE FL FIRE PALIO ELX RST II FIRE SIENA ELX RST II FIRE ');
INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, PrecoProduto, NumeroProduto, NumeroProdutoPesq, CodigoSimilar, CpoAuxProd5, QtdEmbalagem, CpoAuxProd25, PCs) VALUES (6656, 'BRONZINA BIELA AGRALE 2.8 12V STD', 39, NULL, '55.408.005', '55408005', NULL, '', 1, '3500 HD, 3500 HD, 6000,...', ' #NAC_55.408.005 NAC55408005 BRONZINA BIELA AGRALE 2.8 12V STD 8N8220 B131066 BB-1066-P BB1066P CB-619AL CB619AL CHEVROLET FORD GMC NISSAN TROLLER 3500 HD SPRINT EURO 1 4.2 L 18V DOHC L6 SPRINT EURO 1 4.2 L 18V SOHC L6 6000 SPRINT EURO 2 2.8 L 12V SOHC L4 6-150 BLAZER SPRINT EURO 3 2.8 L 12V SOHC L4 F 250 SPRINT EURO 2 4.2 L 18V DOHC L6 FRONTIER FURGOVAN GRAND BLAZER MA 5.0 MA 5000 E MA 6.0 MA 6000 E MARRUÁ S10 SILVERADO X-TERRA ');
INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, PrecoProduto, NumeroProduto, NumeroProdutoPesq, CodigoSimilar, CpoAuxProd5, QtdEmbalagem, CpoAuxProd25, PCs) VALUES (6809, 'BRONZINA MANCAL NISSAN 2.5 16V YD25D STD', 39, NULL, '55.455.007', '55455007', NULL, '', 1, 'FRONTIER, FRONTIER, F...', ' #NAC_55.455.007 NAC55455007 BRONZINA MANCAL NISSAN 2.5 16V YD25D STD 12217-AD200 12217AD200 BC-782-J BC782J M0030782 MS-1229A MS1229A SM802 STD SM802STD FRONTIER YD25ETI 2.5 L 16V DOHC L4 - 2.5 L 16V DOHC L4 PATHFINDER YD25DDTI 2.5 L 16V DOHC L4 ');
INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, PrecoProduto, NumeroProduto, NumeroProdutoPesq, CodigoSimilar, CpoAuxProd5, QtdEmbalagem, CpoAuxProd25, PCs) VALUES (6810, 'BRONZINA MANCAL NISSAN 2.5 16V YD25D +0,25', 39, NULL, '55.455.107', '55455107', NULL, '', 1, 'FRONTIER, FRONTIER, F...', ' #NAC_55.455.107 NAC55455107 BRONZINA MANCAL NISSAN 2.5 16V YD25D +0,25 12217-AD200 12217AD200 BC-782-J BC782J M0030782 MS-1229A MS1229A SM802 025 SM802025 FRONTIER YD25ETI 2.5 L 16V DOHC L4 - 2.5 L 16V DOHC L4 PATHFINDER YD25DDTI 2.5 L 16V DOHC L4 ');
INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, PrecoProduto, NumeroProduto, NumeroProdutoPesq, CodigoSimilar, CpoAuxProd5, QtdEmbalagem, CpoAuxProd25, PCs) VALUES (6811, 'BRONZINA MANCAL NISSAN 2.5 16V YD25D +0,50', 39, NULL, '55.455.207', '55455207', NULL, '', 1, 'FRONTIER, FRONTIER, F...', ' #NAC_55.455.207 NAC55455207 BRONZINA MANCAL NISSAN 2.5 16V YD25D +0,50 12217-AD200 12217AD200 BC-782-J BC782J M0030782 MS-1229A MS1229A SM802 050 SM802050 FRONTIER YD25ETI 2.5 L 16V DOHC L4 - 2.5 L 16V DOHC L4 PATHFINDER YD25DDTI 2.5 L 16V DOHC L4 ');
INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, PrecoProduto, NumeroProduto, NumeroProdutoPesq, CodigoSimilar, CpoAuxProd5, QtdEmbalagem, CpoAuxProd25, PCs) VALUES (11758, 'BRONZINA BIELA AGRALE 2.8 12V STD', 39, NULL, '#NAC_55.408.005', 'NAC55408005', NULL, '', 1, '3500 HD, 3500 HD, 6000,...', ' 55.408.005 55408005 BRONZINA BIELA AGRALE 2.8 12V STD 8N8220 B131066 BB-1066-P BB1066P CB-619AL CB619AL CHEVROLET FORD GMC NISSAN TROLLER 3500 HD SPRINT EURO 1 4.2 L 18V DOHC L6 SPRINT EURO 1 4.2 L 18V SOHC L6 6000 SPRINT EURO 2 2.8 L 12V SOHC L4 6-150 BLAZER SPRINT EURO 3 2.8 L 12V SOHC L4 F 250 SPRINT EURO 2 4.2 L 18V DOHC L6 FRONTIER FURGOVAN GRAND BLAZER MA 5.0 MA 5000 E MA 6.0 MA 6000 E MARRUÁ S10 SILVERADO X-TERRA ');
INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, PrecoProduto, NumeroProduto, NumeroProdutoPesq, CodigoSimilar, CpoAuxProd5, QtdEmbalagem, CpoAuxProd25, PCs) VALUES (11837, 'BRONZINA MANCAL NISSAN 2.5 16V YD25D STD', 39, NULL, '#NAC_55.455.007', 'NAC55455007', NULL, '', 1, 'FRONTIER, FRONTIER, F...', ' 55.455.007 55455007 BRONZINA MANCAL NISSAN 2.5 16V YD25D STD 12217-AD200 12217AD200 BC-782-J BC782J M0030782 MS-1229A MS1229A SM802 STD SM802STD FRONTIER YD25ETI 2.5 L 16V DOHC L4 - 2.5 L 16V DOHC L4 PATHFINDER YD25DDTI 2.5 L 16V DOHC L4 ');
INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, PrecoProduto, NumeroProduto, NumeroProdutoPesq, CodigoSimilar, CpoAuxProd5, QtdEmbalagem, CpoAuxProd25, PCs) VALUES (11838, 'BRONZINA MANCAL NISSAN 2.5 16V YD25D +0,25', 39, NULL, '#NAC_55.455.107', 'NAC55455107', NULL, '', 1, 'FRONTIER, FRONTIER, F...', ' 55.455.107 55455107 BRONZINA MANCAL NISSAN 2.5 16V YD25D +0,25 12217-AD200 12217AD200 BC-782-J BC782J M0030782 MS-1229A MS1229A SM802 025 SM802025 FRONTIER YD25ETI 2.5 L 16V DOHC L4 - 2.5 L 16V DOHC L4 PATHFINDER YD25DDTI 2.5 L 16V DOHC L4 ');
INSERT INTO PRODUTO (CodigoProduto, DescricaoProduto, CodigoGrupoProduto, PrecoProduto, NumeroProduto, NumeroProdutoPesq, CodigoSimilar, CpoAuxProd5, QtdEmbalagem, CpoAuxProd25, PCs) VALUES (11839, 'BRONZINA MANCAL NISSAN 2.5 16V YD25D +0,50', 39, NULL, '#NAC_55.455.207', 'NAC55455207', NULL, '', 1, 'FRONTIER, FRONTIER, F...', ' 55.455.207 55455207 BRONZINA MANCAL NISSAN 2.5 16V YD25D +0,50 12217-AD200 12217AD200 BC-782-J BC782J M0030782 MS-1229A MS1229A SM802 050 SM802050 FRONTIER YD25ETI 2.5 L 16V DOHC L4 - 2.5 L 16V DOHC L4 PATHFINDER YD25DDTI 2.5 L 16V DOHC L4 ');
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (5580, 15365);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (5580, 15366);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (5581, 15365);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (5581, 15366);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (6656, 34828);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (6809, 35368);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (6809, 35369);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (6809, 35374);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (6810, 35368);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (6810, 35369);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (6810, 35374);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (6811, 35368);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (6811, 35369);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (6811, 35374);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (11758, 34828);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (11837, 35368);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (11837, 35369);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (11837, 35374);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (11838, 35368);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (11838, 35369);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (11838, 35374);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (11839, 35368);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (11839, 35369);
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (11839, 35374);
-- Vínculo órfão REAL: a aplicação 15098 não existe na base.
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (1946, 15098);
-- SINTÉTICO: guia de válvula 'BRONZE' (grupo 7) ligada a uma aplicação com bronzinas (grupo 39), para testar o filtro por grupo.
INSERT INTO PRODUTO_APLICACAO (CodigoProduto, CodigoAplicacao) VALUES (3118, 35368);
