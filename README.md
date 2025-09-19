#PROJETO TORRE DE CONTROLE - AERO70

Projeto elabora é uma simulação do funcionamento de uma torre de controle de um aeroporto. 
A ideia da atividade é incluir o enfileiramento, autorização e os relatórios de voos.

#Principais Funcionalidade
 --> Enfileirar voos para decolagem e pouso.
 --> Autorizar voos, verificando:
    -Pistas Abertas;
    -Condições Meteorológico (visibilidade climática);
    -NOTAMs
 --> Exibir status das pistas e filas.
 --> Gerar relatório do turno com a data.

#Principais comandos utilizados
python3 torre/torre.py importar-dados
python3 torre/torre.py listar --por=prioridade
python3 torre/torre.py enfileirar decolagem|pouso --voo ALT123
python3 torre/torre.py autorizar decolagem|pouso --pista 10/28
python3 torre/torre.py status
python3 torre/torre.py relatorio

#Estrutura do Projeto
aero70
 |---torre/
     |---torre.py - código principal
 |---dados/
     |---frota.csv
     |---fila_decolagem.txt
     |---fila_pouso.txt
     |---pilotos.csv
     |---notam.txt
     |---metar.txt
     |---pistas.csv
     |---planos_voo.csv
 |---log/
     |---torre.log
 |---relatorios/
     |--- operacao_20250929.txt
 |---docs
     |---README.md

