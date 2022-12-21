# FSE - Trabalho 1 (2022-2)

| Aluno | Matricula |
| :---:|:---: |
| Jonathan Jorge Barbosa Oliveira | 180103580 |

## 1. Objetivo

Este trabalho tem por objetivo a criação de um sistema distribuído de automação predial para monitoramento e acionamento de sensores e dispositivos de um prédio com múltiplas salas. O sistema deve ser desenvolvido para funcionar em um conjunto de placas Raspberry Pi com um servidor central responsável pelo controle e interface com o usuário e servidores distribuídos para leitura e acionamento dos dispositivos. Dentre os dispositivos envolvidos estão o monitoramento de temperatura e umidade, sensores de presença, sensores de fumaça, sensores de contagem de pessoas, sensores de abertura e fechamento de portas e janelas, acionamento de lâmpadas, aparelhos de ar-condicionado, alarme e aspersores de água em caso de incêndio.

**Demais informações no repositório do enunciado:** [enunciado](https://gitlab.com/fse_fga/trabalhos-2022_2/trabalho-1-2022-2)

## 2. Configuração

*OBS:** È necessário utilizar python 3.9 ou superior

Primeira coisa a se fazer é clonar o repositório:

```bash
git clone https://github.com/Jonathan-Oliveira/FSE_TP1.git
```

Entrar na pasta do projeto:

```bash
cd FSE_TP1
```

E instalar as dependências:

```bash
pip install -r requirements.txt
```

## 2. Como executar

### 2.1. Servidor

Para executar o servidor, basta executar o comando abaixo:

```bash
python server/server.py
```

### 2.2. Clientes

Para executar os clientes, basta executar o comando abaixo:

```bash
python client/client.py
```

## 3. Comandos

Na tela do servidor há instruções de como utilizar o programa. Para executar um comando para todas as salas, basta digitar o comando e apertar enter. Para executar o comando para uma sala específica, basta digitar o  número da sala e o número identificador do comando separados por um espaço. Por exemplo, para acionar a lâmpada 1 da sala 1, basta digitar `1 1`. 
