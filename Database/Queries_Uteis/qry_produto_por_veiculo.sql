Select
	ap.CodigoAplicacao,
	ap.DescricaoAplicacao ,
	ap.Combustivel, 
	ap.FaixaAno,
 	p.*
from APLICACAO ap 
INNER JOIN PRODUTO_APLICACAO pa ON pa.CodigoAplicacao = ap.CodigoAplicacao 
inner join PRODUTO p on p.CodigoProduto = pa.CodigoProduto
Order by ap.DescricaoAplicacao 
;