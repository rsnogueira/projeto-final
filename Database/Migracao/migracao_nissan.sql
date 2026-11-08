-- Migracao: Migrando apenas os Veiculos da Nissan
-- Obtendo todas as aplicacoes (veiculos) associados aos fabricantes desejados.
Select
	cod_aplicao_min as CodigoAplicacao,
	CodigoFabricante,
	CodigoTipoAplicacao,
	FaixaAno,
	Motorizacao,
	Combustivel,
	DescricaoAplicacao,
	AnoInicioFabricacao,
	AnoFimFabricacao 
from 
(
	Select
		min(ap.CodigoAplicacao) as cod_aplicao_min ,
		max(ap.CodigoAplicacao) as cod_aplicao_max ,
		ap.CodigoFabricante,
		ap.CodigoTipoAplicacao,
		ap.ComplementoAplicacao3_1 as FaixaAno ,
		ap.ComplementoAplicacao3_2 as Motorizacao ,
		upper(ap.ComplementoAplicacao3_3) as Combustivel ,
		-- ap.ComplementoAplicacao3_4, Desconhecido !
		ap.DescricaoAplicacao ,
		ap.ComplementoAplicacao3_6 as AnoInicioFabricacao ,
		ap.ComplementoAplicacao3_7 as AnoFimFabricacao 
		, count(1) as quant 
	from APLICACAO ap  
	WHERE 1=1
	-- and ap.CodigoFabricante  in (2,3,8,9,26,32,34,58,71,73,127,128)
	and ap.CodigoFabricante in (73)
	and ap.ComplementoAplicacao3_3 is not null -- Combustível é obrigatório
	and trim(ap.ComplementoAplicacao3_3) <> '' -- Combustível vazio eh erro 
	-- and ap.ComplementoAplicacao3_3 <> '1.4 L 8V SOHC L4' -- Valor indevido.
	and ap.ComplementoAplicacao3_2 is not null -- Motorizacao é obrigatório
	and trim(ap.ComplementoAplicacao3_2) <> '' 
	-- checando repeticoes 
	GROUP BY 
		-- ap.CodigoAplicacao,
		ap.CodigoFabricante,
		ap.CodigoTipoAplicacao,
		ap.ComplementoAplicacao3_1,
		ap.ComplementoAplicacao3_2 ,
		ap.ComplementoAplicacao3_3 ,
		ap.DescricaoAplicacao ,
		ap.ComplementoAplicacao3_6 ,
		ap.ComplementoAplicacao3_7
	-- having count(1) >= 2 
	order by quant desc
)
where quant = 1 
;

-- Conclusao. Temos repeticoes.
-- Há 89 veículos que tem repetições. E aí?

-- Verificando combustiveis.
-- Quais sao os valores na base?
Select
	ap.ComplementoAplicacao3_3 as Combustivel  
	, count(1) as quant 
from APLICACAO ap
WHERE 1=1
	and ap.CodigoFabricante  in (2,3,8,9,26,32,34,58,71,73,127,128)
	and ap.ComplementoAplicacao3_3 is not null -- Combustível é obrigatório
	and trim(ap.ComplementoAplicacao3_3) <> '' -- Valor vazio eh erro.
	and ap.ComplementoAplicacao3_3 <> '1.4 L 8V SOHC L4' -- Valor indevido.
group by ap.ComplementoAplicacao3_3 
;

-- Lista de Aplicacoes (veiculos) nao repetidos da Nissan,
-- Versus os seus Produtos (suas pecas).
Select
	CodigoProduto,
	CodigoAplicacao
from PRODUTO_APLICACAO pa 
where CodigoAplicacao in 
(
	Select cod_aplicao_min
	from 
	(
		Select
			min(ap.CodigoAplicacao) as cod_aplicao_min ,
			max(ap.CodigoAplicacao) as cod_aplicao_max ,
			ap.CodigoFabricante,
			ap.CodigoTipoAplicacao,
			ap.ComplementoAplicacao3_1 as FaixaAno ,
			ap.ComplementoAplicacao3_2 as Motorizacao ,
			upper(ap.ComplementoAplicacao3_3) as Combustivel ,
			-- ap.ComplementoAplicacao3_4, Desconhecido !
			ap.DescricaoAplicacao ,
			ap.ComplementoAplicacao3_6 as AnoInicioFabricacao ,
			ap.ComplementoAplicacao3_7 as AnoFimFabricacao 
			, count(1) as quant 
		from APLICACAO ap  
		WHERE 1=1
		-- and ap.CodigoFabricante  in (2,3,8,9,26,32,34,58,71,73,127,128)
		and ap.CodigoFabricante in (73)
		and ap.ComplementoAplicacao3_3 is not null -- Combustível é obrigatório
		and trim(ap.ComplementoAplicacao3_3) <> '' -- Combustível vazio eh erro 
		-- and ap.ComplementoAplicacao3_3 <> '1.4 L 8V SOHC L4' -- Valor indevido.
		and ap.ComplementoAplicacao3_2 is not null -- Motorizacao é obrigatório
		and trim(ap.ComplementoAplicacao3_2) <> '' 
		-- checando repeticoes 
		GROUP BY 
			-- ap.CodigoAplicacao,
			ap.CodigoFabricante,
			ap.CodigoTipoAplicacao,
			ap.ComplementoAplicacao3_1,
			ap.ComplementoAplicacao3_2 ,
			ap.ComplementoAplicacao3_3 ,
			ap.DescricaoAplicacao ,
			ap.ComplementoAplicacao3_6 ,
			ap.ComplementoAplicacao3_7
	)
	where quant = 1 
);
