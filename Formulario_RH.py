import os
import re
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import streamlit as st

# =====================
# Segredos / Config (12-factor)
# =====================

def get_secret(name, default=None):
    return os.getenv(name) or st.secrets.get(name, default)

NOME_EMPRESA  = get_secret("NOME_EMPRESA",  "Provion Seguros")
EMAIL_DESTINO = get_secret("EMAIL_DESTINO", "naosei@provion.com.br")
EMAIL_FROM    = get_secret("EMAIL_FROM",    "rfrugoni.provion@gmail.com")
SMTP_HOST     = get_secret("SMTP_HOST",     "smtp.gmail.com")
SMTP_PORT     = int(get_secret("SMTP_PORT", 587))
SMTP_USER     = get_secret("SMTP_USER",     EMAIL_FROM)
SMTP_PASS     = get_secret("EMAIL_APP_PASSWORD")  # senha de app do Gmail

# =====================
# Layout (deve ser o primeiro st.*)
# =====================
st.set_page_config(page_title="Formulário de Candidato", page_icon="provion.ico", layout="centered")
st.image("logo_provion.png", width=500)
st.title("Formulário de Candidato")

# =====================
# Constantes e utilidades
# =====================
UFS = sorted([
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
    "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"
])

@st.cache_data(show_spinner=False, ttl=3600)
def buscar_cep(cep: str):
    """Consulta ViaCEP e retorna dict com logradouro, bairro, cidade, uf ou None."""
    cep8 = re.sub(r"\D", "", cep or "")
    if len(cep8) != 8:
        return None
    url = f"https://viacep.com.br/ws/{cep8}/json/"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()
        if data.get("erro"):
            return None
        return {
            "logradouro": data.get("logradouro", ""),
            "bairro": data.get("bairro", ""),
            "cidade": data.get("localidade", ""),
            "uf": data.get("uf", ""),
        }
    except Exception:
        return None


def validar_cpf(cpf: str) -> bool:
    """Valida CPF pelos dígitos verificadores."""
    n = re.sub(r"\D", "", cpf or "")
    if len(n) != 11 or n == n[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(n[num]) * ((i + 1) - num) for num in range(i))
        digito = ((soma * 10) % 11) % 10
        if digito != int(n[i]):
            return False
    return True


def so_digitos(valor: str) -> str:
    return re.sub(r"\D", "", (valor or ""))

# =====================
# Estado inicial (session)
# =====================
for k, v in {"cep":"", "logradouro":"", "numero":"", "complemento":"", "bairro":"", "cidade":"", "uf_endereco":""}.items():
    st.session_state.setdefault(k, v)

# =====================
# Texto LGPD
# =====================
st.markdown(
    """
    As informações fornecidas neste formulário serão tratadas em **estrita conformidade com a LGPD (Lei nº 13.709/2018)**,
    utilizadas exclusivamente para fins de **recrutamento e seleção**, armazenadas em ambiente seguro e com acesso restrito.
    """
)

# =====================
# Formulário
# =====================
with st.form("form_candidato"):
    st.subheader("Dados da Vaga")
    dados_vaga = st.text_area(
        "Descreva a vaga para a qual está se candidatando",
        placeholder="Ex: Analista de Marketing - Rio de Janeiro/RJ",
        help="Informe o título e local da vaga (ex: Analista de Marketing - Rio de Janeiro/RJ)",
    )
    pretensao_salarial = st.number_input(
        "Pretensão Salarial (R$)", min_value=0.0, step=100.0, format="%.2f",
        help="Informe o valor bruto mensal desejado",
    )

    st.subheader("Dados Pessoais")
    col_a, col_b = st.columns([3, 2])
    with col_a:
        nome_completo = st.text_input("Nome Completo")
    with col_b:
        data_nascimento = st.date_input("Data de Nascimento")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        cpf = st.text_input("CPF (somente números)", max_chars=11)
        if cpf and not cpf.isdigit():
            st.error("Digite apenas números no CPF")
        elif cpf and not validar_cpf(cpf):
            st.warning("CPF informado não passou na validação de dígitos verificadores.")
    with col2:
        identidade = st.text_input("Identidade (RG)")
    with col3:
        orgao_expedidor = st.text_input("Órgão Expedidor")

    col4, col5 = st.columns([2, 2])
    with col4:
        data_expedicao = st.date_input("Data de Expedição")
    with col5:
        uf_rg = st.selectbox("UF de Expedição (RG)", options=["Selecione a UF"] + UFS, index=0)

    st.divider()

    st.subheader("Endereço")
    c1, c2 = st.columns([2,1])
    with c1:
        cep_input = st.text_input("CEP (somente números)", value=st.session_state.cep, max_chars=8, placeholder="00000000")
    with c2:
        buscar = st.form_submit_button("Buscar CEP", use_container_width=True)

    if buscar:
        cep_num = so_digitos(cep_input)
        if len(cep_num) != 8:
            st.error("Informe um CEP válido com 8 dígitos.")
        else:
            info = buscar_cep(cep_num)
            if not info:
                st.error("CEP não encontrado na base do ViaCEP.")
            else:
                st.session_state.update({
                    "cep": cep_num,
                    "logradouro": info["logradouro"],
                    "bairro": info["bairro"],
                    "cidade": info["cidade"],
                    "uf_endereco": info["uf"],
                })
                st.success("Endereço preenchido automaticamente a partir do CEP.")

    l1, l2, l3 = st.columns([3,1,2])
    with l1:
        logradouro = st.text_input("Endereço (Rua/Av.)", value=st.session_state.logradouro)
    with l2:
        numero = st.text_input("Número (0 se s/ nº)", value=st.session_state.numero)
    with l3:
        complemento = st.text_input("Complemento (Apto, Bloco, etc.)", value=st.session_state.complemento)

    l4, l5, l6 = st.columns([2,2,1])
    with l4:
        bairro = st.text_input("Bairro", value=st.session_state.bairro)
    with l5:
        cidade = st.text_input("Cidade", value=st.session_state.cidade)
    with l6:
        uf_endereco = st.selectbox(
            "UF",
            options=["Selecione a UF"] + UFS,
            index=( ["Selecione a UF"] + UFS ).index(st.session_state.uf_endereco) if st.session_state.uf_endereco in UFS else 0,
        )

    st.divider()

    st.subheader("Contato")
    colt1, colt2 = st.columns([2,3])
    with colt1:
        telefone = st.text_input("Telefone (DDD + número)", placeholder="11999999999")
    with colt2:
        email = st.text_input("E-mail").strip()
        padrao_email = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
        if email and not re.match(padrao_email, email):
            st.error("Digite um e-mail válido (ex: usuario@dominio.com)")

    st.divider()

    st.subheader("Situação Familiar")
    colsf1, colsf2, colsf3 = st.columns([2,2,2])
    with colsf1:
        estado_civil = st.selectbox("Estado Civil", ["Selecione", "Solteiro(a)", "Casado(a)", "União Estável", "Divorciado(a)", "Viúvo(a)", "Separado(a)"])
    with colsf2:
        sexo = st.selectbox("Sexo", ["Selecione", "Masculino", "Feminino", "Outro"])
    with colsf3:
        pcd = st.selectbox("PCD?", ["Selecione", "Sim", "Não"])

    filhos = st.number_input("Número de Filhos (0 se não tiver)", min_value=0, step=1)

    st.markdown("**Dependentes no Imposto de Renda**")
    dependentes_ir = st.number_input("Quantidade de Dependentes IR", min_value=0, step=1)
    if dependentes_ir > filhos:
        st.error("O número de dependentes no IR não pode ser maior que o número de filhos.")
    dependentes = []
    for i in range(int(dependentes_ir)):
        st.markdown(f"**Dependente {i+1}**")
        d1, d2, d3 = st.columns([3,2,2])
        with d1:
            dep_nome = st.text_input(f"Nome do Dependente {i+1}", key=f"dep_nome_{i}")
        with d2:
            dep_parentesco = st.selectbox(
                f"Grau de Parentesco {i+1}",
                ["Selecione", "Filho(a)", "Cônjuge", "Pai", "Mãe", "Outro"],
                key=f"dep_parentesco_{i}",
            )
        with d3:
            dep_cpf = st.text_input(f"CPF do Dependente {i+1} (somente números)", max_chars=11, key=f"dep_cpf_{i}")
            if dep_cpf and (not dep_cpf.isdigit() or len(dep_cpf) != 11 or not validar_cpf(dep_cpf)):
                st.warning(f"CPF do Dependente {i+1} parece inválido.")
        dependentes.append({"nome": dep_nome, "parentesco": dep_parentesco, "cpf": dep_cpf})

    st.divider()

    st.subheader("Histórico Profissional")
    st.markdown("**Último Emprego**")
    ue1, ue2 = st.columns(2)
    with ue1:
        ultimo_emprego = st.text_input("Empresa (Último)")
        atividades_ultimo_cargo = st.text_area("Atividades (Último Cargo)")
    with ue2:
        ultimo_cargo = st.text_input("Cargo (Último)")
        data_admissao = st.date_input("Data de Admissão (Último)")
        data_desligamento = st.date_input("Data de Desligamento (Último)")
    ue3, ue4 = st.columns(2)
    with ue3:
        motivo_saida = st.text_input("Motivo da Saída (Último)")
    with ue4:
        telefone_ultimo_emprego = st.text_input("Telefone (Último) — DDD+nº")
        contato_ultimo_emprego = st.text_input("Contato (Gestor/RH)", key="contato_ultimo_emprego")

    st.markdown("**Penúltimo Emprego**")
    pe1, pe2 = st.columns(2)
    with pe1:
        penultimo_emprego = st.text_input("Empresa (Penúltimo)")
        atividades_penultimo_cargo = st.text_area("Atividades (Penúltimo Cargo)")
    with pe2:
        penultimo_cargo = st.text_input("Cargo (Penúltimo)")
        data_admissao_penultimo = st.date_input("Data de Admissão (Penúltimo)")
        data_desligamento_penultimo = st.date_input("Data de Desligamento (Penúltimo)")
    pe3, pe4 = st.columns(2)
    with pe3:
        motivo_saida_penultimo = st.text_input("Motivo da Saída (Penúltimo)")
    with pe4:
        telefone_penultimo_emprego = st.text_input("Telefone (Penúltimo) — DDD+nº")
        contato_penultimo_emprego = st.text_input("Contato (Gestor/RH)", key="contato_penultimo_emprego")

    st.divider()

    st.subheader("Formação Acadêmica e Idiomas")
    escolaridade = st.selectbox("Nível de Escolaridade", [
        "Selecione", "Ensino Fundamental Incompleto", "Ensino Fundamental Completo",
        "Ensino Médio Incompleto", "Ensino Médio Completo", "Ensino Superior Incompleto",
        "Ensino Superior Completo", "Pós-graduação", "Mestrado", "Doutorado",
    ])
    colfa1, colfa2, colfa3 = st.columns([2,2,1])
    with colfa1:
        curso = st.text_input("Curso")
        instituicao = st.text_input("Instituição de Ensino")
    with colfa2:
        ano_conclusao = st.number_input("Ano de Conclusão", min_value=1900, max_value=2100, step=1)
        situacao = st.selectbox("Situação", ["Selecione", "Cursando", "Concluído", "Trancado", "Interrompido"])    
    with colfa3:
        outra_formacao = st.text_input("Outra Formação")

    st.markdown("**Idiomas**")
    idiomas = st.multiselect("Idiomas", ["Inglês", "Espanhol", "Francês", "Alemão", "Mandarim", "Italiano"])
    nivel_idioma = st.selectbox("Nível do Idioma", ["Selecione", "Básico", "Intermediário", "Avançado", "Fluente"])  

    st.divider()

    # Consentimento LGPD
    texto_consentimento = (
        f"Você concorda com os termos listados? Os dados pessoais informados neste formulário serão coletados e tratados pela {NOME_EMPRESA} "
        "em conformidade com a Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018 - LGPD). "
        "O tratamento será realizado unicamente para finalidades relacionadas ao processo de recrutamento e seleção, "
        "em ambiente protegido e controlado, com medidas técnicas e administrativas adequadas para garantir a segurança, "
        "confidencialidade e integridade das informações."
    )
    consentiu = st.checkbox(texto_consentimento, value=False)

    enviar = st.form_submit_button("Enviar Formulário")

# =====================
# Pós-submit
# =====================
if enviar:
    erros = []

    if not nome_completo:
        erros.append("Preencha o Nome Completo.")
    if not cpf or not cpf.isdigit() or len(cpf) != 11 or not validar_cpf(cpf):
        erros.append("CPF inválido (11 dígitos e verificador).")
    if uf_rg == "Selecione a UF":
        erros.append("Selecione a UF de Expedição (RG).")
    if uf_endereco == "Selecione a UF":
        erros.append("Selecione a UF do Endereço.")
    padrao_email = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
    if not email or not re.match(padrao_email, email):
        erros.append("E-mail inválido.")
    if not consentiu:
        erros.append("É necessário concordar com os termos de LGPD.")

    if erros:
        st.error("Corrija os itens antes de enviar:\n- " + "\n- ".join(erros))
        st.stop()

    # Normalizações
    cep_num = so_digitos(cep_input)
    telefone_str = so_digitos(telefone)

    # Monta corpo do e-mail
    corpo_email = f"""
    Formulário de Candidato

    Vaga: {dados_vaga}
    Pretensão Salarial (R$): {pretensao_salarial:.2f}

    Nome: {nome_completo}
    Data de Nascimento: {data_nascimento}
    CPF: {cpf}
    RG: {identidade} - Órgão: {orgao_expedidor} - UF Expedição: {uf_rg} - Data: {data_expedicao}

    Endereço:
    CEP: {cep_num}
    Logradouro: {logradouro}
    Número: {numero}
    Complemento: {complemento}
    Bairro: {bairro}
    Cidade: {cidade}
    UF: {uf_endereco}

    Contato:
    Telefone: {telefone_str}
    E-mail: {email}

    Situação Familiar:
    Estado Civil: {estado_civil}
    Sexo: {sexo}
    PCD: {pcd}
    Filhos: {filhos}

    Dependentes IR: {len(dependentes)}
    Dependentes (JSON): {dependentes}

    Último Emprego: {ultimo_emprego} | Cargo: {ultimo_cargo}
    Atividades (último): {atividades_ultimo_cargo}
    Período: {data_admissao} a {data_desligamento}
    Motivo Saída: {motivo_saida}
    Telefone (último): {telefone_ultimo_emprego}
    Contato (último): {contato_ultimo_emprego}

    Penúltimo Emprego: {penultimo_emprego} | Cargo: {penultimo_cargo}
    Atividades (penúltimo): {atividades_penultimo_cargo}
    Período: {data_admissao_penultimo} a {data_desligamento_penultimo}
    Motivo Saída (penúltimo): {motivo_saida_penultimo}
    Telefone (penúltimo): {telefone_penultimo_emprego}
    Contato (penúltimo): {contato_penultimo_emprego}

    Formação:
    Escolaridade: {escolaridade}
    Curso: {curso}
    Instituição: {instituicao}
    Ano Conclusão: {ano_conclusao}
    Situação: {situacao}

    Idiomas: {idiomas}
    Nível geral: {nivel_idioma}

    LGPD: consentimento = {bool(consentiu)} em {datetime.now().isoformat()}
    """.strip()

    # Verifica segredo de e-mail somente no envio
    if not SMTP_PASS:
        st.error("EMAIL_APP_PASSWORD não configurado (Secrets/Env). Envio bloqueado.")
        st.stop()

    # Envio por SMTP (STARTTLS)
    msg = MIMEMultipart()
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_DESTINO
    msg['Subject'] = "Nova resposta - Questionário RECANORTE"
    msg.attach(MIMEText(corpo_email, 'plain', 'utf-8'))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        st.success("✅ Respostas enviadas com sucesso!")
    except Exception as e:
        st.error(f"❌ Erro ao enviar: {e}")
