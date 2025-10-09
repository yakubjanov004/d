--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: business_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.business_type AS ENUM (
    'B2B',
    'B2C'
);


ALTER TYPE public.business_type OWNER TO postgres;

--
-- Name: connection_order_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.connection_order_status AS ENUM (
    'in_manager',
    'in_junior_manager',
    'in_controller',
    'in_technician',
    'in_repairs',
    'in_warehouse',
    'in_technician_work',
    'completed',
    'between_controller_technician',
    'cancelled'
);


ALTER TYPE public.connection_order_status OWNER TO postgres;

--
-- Name: smart_service_category; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.smart_service_category AS ENUM (
    'aqlli_avtomatlashtirilgan_xizmatlar',
    'xavfsizlik_kuzatuv_tizimlari',
    'internet_tarmoq_xizmatlari',
    'energiya_yashil_texnologiyalar',
    'multimediya_aloqa_tizimlari',
    'maxsus_qoshimcha_xizmatlar'
);


ALTER TYPE public.smart_service_category OWNER TO postgres;

--
-- Name: smart_service_type; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN public.smart_service_type AS text
	CONSTRAINT smart_service_type_check CHECK ((VALUE = ANY (ARRAY['aqlli_uy_tizimlarini_ornatish_sozlash'::text, 'aqlli_yoritish_smart_lighting_tizimlari'::text, 'aqlli_termostat_iqlim_nazarati_tizimlari'::text, 'smart_lock_internet_orqali_boshqariladigan_eshik_qulfi_tizimlari'::text, 'aqlli_rozetalar_energiya_monitoring_tizimlari'::text, 'uyni_masofadan_boshqarish_qurilmalari_yagona_uzim_orqali_boshqarish'::text, 'aqlli_pardalari_jaluz_tizimlari'::text, 'aqlli_malahiy_texnika_integratsiyasi'::text, 'videokuzatuv_kameralari_ornatish_ip_va_analog'::text, 'kamera_arxiv_tizimlari_bulutli_saqlash_xizmatlari'::text, 'domofon_tizimlari_ornatish'::text, 'xavfsizlik_signalizatsiyasi_harakat_sensorlarini_ornatish'::text, 'yong_signalizatsiyasi_tizimlari'::text, 'gaz_sizish_sav_toshqinliqqa_qarshi_tizimlar'::text, 'yuzni_tanish_face_recognition_tizimlari'::text, 'avtomatik_eshik_darvoza_boshqaruv_tizimlari'::text, 'wi_fi_tarmoqlarini_ornatish_sozlash'::text, 'wi_fi_qamrov_zonasini_kengaytirish_access_point'::text, 'mobil_aloqa_signalini_kuchaytirish_repeater'::text, 'ofis_va_uy_uchun_lokal_tarmoq_lan_qurish'::text, 'internet_provayder_xizmatlarini_ulash'::text, 'server_va_nas_qurilmalarini_ornatish'::text, 'bulutli_fayl_almashish_zaxira_tizimlari'::text, 'vpn_va_xavfsiz_internet_ulanishlarini_tashkil_qilish'::text, 'quyosh_panellarini_ornatish_ulash'::text, 'quyosh_batareyalari_orqali_energiya_saqlash_tizimlari'::text, 'shamol_generatorlarini_ornatish'::text, 'elektr_energiyasini_tejovchi_yoritish_tizimlari'::text, 'avtomatik_suv_orish_tizimlari_smart_irrigation'::text, 'smart_tv_ornatish_ulash'::text, 'uy_kinoteatri_tizimlari_ornatish'::text, 'audio_tizimlar_multiroom'::text, 'ip_telefoniya_mini_ats_tizimlarini_tashkil_qilish'::text, 'video_konferensiya_tizimlari'::text, 'interaktiv_taqdimot_tizimlari_proyektor_led_ekran'::text, 'aqlli_ofis_tizimlarini_ornatish'::text, 'data_markaz_server_room_loyihalash_montaj_qilish'::text, 'qurilma_tizimlar_uchun_texnik_xizmat_korsatish'::text, 'dasturiy_taminotni_ornatish_yangilash'::text, 'iot_internet_of_things_qurilmalarini_integratsiya_qilish'::text, 'qurilmalarni_masofadan_boshqarish_tizimlarini_sozlash'::text, 'suniy_intellekt_asosidagi_uy_ofis_boshqaruv_tizimlari'::text])));


ALTER DOMAIN public.smart_service_type OWNER TO postgres;

--
-- Name: staff_order_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.staff_order_status AS ENUM (
    'new',
    'in_call_center_operator',
    'in_call_center_supervisor',
    'in_manager',
    'in_junior_manager',
    'in_controller',
    'in_technician',
    'in_diagnostics',
    'in_repairs',
    'in_warehouse',
    'in_technician_work',
    'completed',
    'between_controller_technician',
    'cancelled',
    'in_progress',
    'assigned_to_technician'
);


ALTER TYPE public.staff_order_status OWNER TO postgres;

--
-- Name: technician_order_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.technician_order_status AS ENUM (
    'in_controller',
    'in_technician',
    'in_diagnostics',
    'in_repairs',
    'in_warehouse',
    'in_technician_work',
    'completed',
    'between_controller_technician',
    'in_call_center_supervisor',
    'in_call_center_operator',
    'cancelled'
);


ALTER TYPE public.technician_order_status OWNER TO postgres;

--
-- Name: type_of_zayavka; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.type_of_zayavka AS ENUM (
    'connection',
    'technician'
);


ALTER TYPE public.type_of_zayavka OWNER TO postgres;

--
-- Name: user_role; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.user_role AS ENUM (
    'admin',
    'client',
    'manager',
    'junior_manager',
    'controller',
    'technician',
    'warehouse',
    'callcenter_supervisor',
    'callcenter_operator'
);


ALTER TYPE public.user_role OWNER TO postgres;

--
-- Name: create_user_sequential(bigint, text, text, text, public.user_role); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.create_user_sequential(p_telegram_id bigint, p_username text DEFAULT NULL::text, p_full_name text DEFAULT NULL::text, p_phone text DEFAULT NULL::text, p_role public.user_role DEFAULT 'client'::public.user_role) RETURNS TABLE(user_id integer, user_telegram_id bigint, user_username text, user_full_name text, user_phone text, user_role public.user_role, user_created_at timestamp with time zone)
    LANGUAGE plpgsql
    AS $$
DECLARE
    new_user_id INTEGER;
    ret_user_id INTEGER;
    ret_telegram_id BIGINT;
    ret_username TEXT;
    ret_full_name TEXT;
    ret_phone TEXT;
    ret_role user_role;
    ret_created_at TIMESTAMPTZ;
BEGIN
    -- Get next sequential ID
    SELECT get_next_sequential_user_id() INTO new_user_id;
    
    -- Insert user with sequential ID
    INSERT INTO users (id, telegram_id, username, full_name, phone, role)
    VALUES (new_user_id, p_telegram_id, p_username, p_full_name, p_phone, p_role)
    ON CONFLICT (telegram_id) DO UPDATE SET
        username = EXCLUDED.username,
        full_name = EXCLUDED.full_name,
        phone = EXCLUDED.phone,
        updated_at = NOW()
    RETURNING users.id, users.telegram_id, users.username, users.full_name, users.phone, users.role, users.created_at
    INTO ret_user_id, ret_telegram_id, ret_username, ret_full_name, ret_phone, ret_role, ret_created_at;
    
    create_user_sequential.user_id := ret_user_id;
    create_user_sequential.user_telegram_id := ret_telegram_id;
    create_user_sequential.user_username := ret_username;
    create_user_sequential.user_full_name := ret_full_name;
    create_user_sequential.user_phone := ret_phone;
    create_user_sequential.user_role := ret_role;
    create_user_sequential.user_created_at := ret_created_at;
    
    RETURN NEXT;
END;
$$;


ALTER FUNCTION public.create_user_sequential(p_telegram_id bigint, p_username text, p_full_name text, p_phone text, p_role public.user_role) OWNER TO postgres;

--
-- Name: FUNCTION create_user_sequential(p_telegram_id bigint, p_username text, p_full_name text, p_phone text, p_role public.user_role); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.create_user_sequential(p_telegram_id bigint, p_username text, p_full_name text, p_phone text, p_role public.user_role) IS 'Creates user with sequential ID';


--
-- Name: get_next_sequential_user_id(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.get_next_sequential_user_id() RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    next_id INTEGER;
BEGIN
    -- Get the next value from our custom sequence
    SELECT nextval('user_sequential_id_seq') INTO next_id;
    
    -- Check if this ID already exists in users table
    WHILE EXISTS (SELECT 1 FROM users WHERE id = next_id) LOOP
        SELECT nextval('user_sequential_id_seq') INTO next_id;
    END LOOP;
    
    RETURN next_id;
END;
$$;


ALTER FUNCTION public.get_next_sequential_user_id() OWNER TO postgres;

--
-- Name: FUNCTION get_next_sequential_user_id(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.get_next_sequential_user_id() IS 'Returns next available sequential user ID';


--
-- Name: reset_user_sequential_sequence(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.reset_user_sequential_sequence() RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    max_id INTEGER;
BEGIN
    -- Get the maximum existing user ID
    SELECT COALESCE(MAX(id), 0) + 1 INTO max_id FROM users;
    
    -- Reset the sequence to start from the next available ID
    PERFORM setval('user_sequential_id_seq', max_id, false);
END;
$$;


ALTER FUNCTION public.reset_user_sequential_sequence() OWNER TO postgres;

--
-- Name: FUNCTION reset_user_sequential_sequence(); Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON FUNCTION public.reset_user_sequential_sequence() IS 'Resets sequence to match existing data';


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: akt_documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.akt_documents (
    id bigint NOT NULL,
    request_id bigint,
    request_type text,
    akt_number text NOT NULL,
    file_path text NOT NULL,
    file_hash text NOT NULL,
    sent_to_client_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT akt_documents_request_type_check CHECK ((request_type = ANY (ARRAY['connection'::text, 'technician'::text, 'staff'::text])))
);


ALTER TABLE public.akt_documents OWNER TO postgres;

--
-- Name: akt_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.akt_documents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.akt_documents_id_seq OWNER TO postgres;

--
-- Name: akt_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.akt_documents_id_seq OWNED BY public.akt_documents.id;


--
-- Name: akt_ratings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.akt_ratings (
    id bigint NOT NULL,
    request_id bigint,
    request_type text,
    rating integer,
    comment text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT akt_ratings_rating_check CHECK (((rating >= 0) AND (rating <= 5))),
    CONSTRAINT akt_ratings_request_type_check CHECK ((request_type = ANY (ARRAY['connection'::text, 'technician'::text, 'staff'::text])))
);


ALTER TABLE public.akt_ratings OWNER TO postgres;

--
-- Name: akt_ratings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.akt_ratings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.akt_ratings_id_seq OWNER TO postgres;

--
-- Name: akt_ratings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.akt_ratings_id_seq OWNED BY public.akt_ratings.id;


--
-- Name: connection_orders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.connection_orders (
    id bigint NOT NULL,
    application_number character varying(50),
    user_id bigint,
    region text,
    address text,
    tarif_id bigint,
    business_type public.business_type DEFAULT 'B2C'::public.business_type NOT NULL,
    longitude double precision,
    latitude double precision,
    jm_notes text,
    cancellation_note text,
    is_active boolean DEFAULT true NOT NULL,
    status public.connection_order_status DEFAULT 'in_manager'::public.connection_order_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    diagnostics text
);


ALTER TABLE public.connection_orders OWNER TO postgres;

--
-- Name: COLUMN connection_orders.diagnostics; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.connection_orders.diagnostics IS 'Diagnostics information for connection orders, similar to technician_orders';


--
-- Name: connection_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.connection_orders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.connection_orders_id_seq OWNER TO postgres;

--
-- Name: connection_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.connection_orders_id_seq OWNED BY public.connection_orders.id;


--
-- Name: connections; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.connections (
    id bigint NOT NULL,
    sender_id bigint,
    recipient_id bigint,
    connection_id bigint,
    technician_id bigint,
    staff_id bigint,
    sender_status text,
    recipient_status text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.connections OWNER TO postgres;

--
-- Name: connections_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.connections_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.connections_id_seq OWNER TO postgres;

--
-- Name: connections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.connections_id_seq OWNED BY public.connections.id;


--
-- Name: material_and_technician; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.material_and_technician (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    material_id bigint NOT NULL,
    quantity integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.material_and_technician OWNER TO postgres;

--
-- Name: material_and_technician_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.material_and_technician_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.material_and_technician_id_seq OWNER TO postgres;

--
-- Name: material_and_technician_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.material_and_technician_id_seq OWNED BY public.material_and_technician.id;


--
-- Name: material_issued; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.material_issued (
    id bigint NOT NULL,
    material_id bigint NOT NULL,
    quantity integer NOT NULL,
    price numeric(10,2) NOT NULL,
    total_price numeric(10,2) NOT NULL,
    issued_by bigint NOT NULL,
    issued_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    material_name text,
    material_unit text,
    is_approved boolean DEFAULT false,
    application_number character varying(50),
    request_type character varying(20) DEFAULT 'connection'::character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT material_issued_quantity_check CHECK ((quantity > 0))
);


ALTER TABLE public.material_issued OWNER TO postgres;

--
-- Name: material_issued_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.material_issued_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.material_issued_id_seq OWNER TO postgres;

--
-- Name: material_issued_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.material_issued_id_seq OWNED BY public.material_issued.id;


--
-- Name: material_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.material_requests (
    id bigint NOT NULL,
    description text,
    user_id bigint,
    applications_id bigint,
    material_id bigint,
    connection_order_id bigint,
    technician_order_id bigint,
    staff_order_id bigint,
    quantity integer DEFAULT 1,
    price numeric DEFAULT 0,
    total_price numeric DEFAULT 0,
    source_type character varying(20) DEFAULT 'warehouse'::character varying,
    warehouse_approved boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.material_requests OWNER TO postgres;

--
-- Name: material_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.material_requests_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.material_requests_id_seq OWNER TO postgres;

--
-- Name: material_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.material_requests_id_seq OWNED BY public.material_requests.id;


--
-- Name: materials; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.materials (
    id bigint NOT NULL,
    name text,
    price numeric,
    description text,
    quantity integer DEFAULT 0,
    serial_number text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.materials OWNER TO postgres;

--
-- Name: materials_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.materials_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.materials_id_seq OWNER TO postgres;

--
-- Name: materials_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.materials_id_seq OWNED BY public.materials.id;


--
-- Name: media_files; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.media_files (
    id bigint NOT NULL,
    file_path text NOT NULL,
    file_type text,
    file_size bigint,
    original_name text,
    mime_type text,
    category text,
    related_table text,
    related_id bigint,
    uploaded_by bigint,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.media_files OWNER TO postgres;

--
-- Name: media_files_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.media_files_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.media_files_id_seq OWNER TO postgres;

--
-- Name: media_files_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.media_files_id_seq OWNED BY public.media_files.id;


--
-- Name: reports; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reports (
    id bigint NOT NULL,
    title text NOT NULL,
    description text,
    created_by bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.reports OWNER TO postgres;

--
-- Name: reports_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.reports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reports_id_seq OWNER TO postgres;

--
-- Name: reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.reports_id_seq OWNED BY public.reports.id;


--
-- Name: smart_service_orders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.smart_service_orders (
    id bigint NOT NULL,
    application_number character varying(50),
    user_id bigint,
    category public.smart_service_category NOT NULL,
    service_type public.smart_service_type NOT NULL,
    address text NOT NULL,
    longitude double precision,
    latitude double precision,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.smart_service_orders OWNER TO postgres;

--
-- Name: smart_service_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.smart_service_orders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.smart_service_orders_id_seq OWNER TO postgres;

--
-- Name: smart_service_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.smart_service_orders_id_seq OWNED BY public.smart_service_orders.id;


--
-- Name: staff_orders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.staff_orders (
    id bigint NOT NULL,
    application_number character varying(50),
    user_id bigint,
    phone text,
    region text,
    abonent_id text,
    tarif_id bigint,
    address text,
    description text,
    problem_description text,
    diagnostics text,
    jm_notes text,
    cancellation_note text,
    business_type public.business_type DEFAULT 'B2C'::public.business_type NOT NULL,
    status public.staff_order_status DEFAULT 'new'::public.staff_order_status NOT NULL,
    type_of_zayavka public.type_of_zayavka DEFAULT 'connection'::public.type_of_zayavka NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_by_role public.user_role,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.staff_orders OWNER TO postgres;

--
-- Name: staff_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.staff_orders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.staff_orders_id_seq OWNER TO postgres;

--
-- Name: staff_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.staff_orders_id_seq OWNED BY public.staff_orders.id;


--
-- Name: tarif; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tarif (
    id bigint NOT NULL,
    name text,
    picture text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tarif OWNER TO postgres;

--
-- Name: tarif_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tarif_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tarif_id_seq OWNER TO postgres;

--
-- Name: tarif_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tarif_id_seq OWNED BY public.tarif.id;


--
-- Name: technician_orders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.technician_orders (
    id bigint NOT NULL,
    application_number character varying(50),
    user_id bigint,
    region text,
    abonent_id text,
    address text,
    media text,
    business_type public.business_type DEFAULT 'B2C'::public.business_type NOT NULL,
    longitude double precision,
    latitude double precision,
    description text,
    description_ish text,
    description_operator text,
    cancellation_note text,
    status public.technician_order_status DEFAULT 'in_controller'::public.technician_order_status NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.technician_orders OWNER TO postgres;

--
-- Name: technician_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.technician_orders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.technician_orders_id_seq OWNER TO postgres;

--
-- Name: technician_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.technician_orders_id_seq OWNED BY public.technician_orders.id;


--
-- Name: user_sequential_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_sequential_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_sequential_id_seq OWNER TO postgres;

--
-- Name: SEQUENCE user_sequential_id_seq; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON SEQUENCE public.user_sequential_id_seq IS 'Sequential ID generator for users table';


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id bigint NOT NULL,
    telegram_id bigint,
    full_name text,
    username text,
    phone text,
    language character varying(5) DEFAULT 'uz'::character varying NOT NULL,
    region character varying(20),
    address text,
    role public.user_role,
    abonent_id text,
    is_blocked boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT users_region_check CHECK (((region)::text = ANY ((ARRAY['tashkent_city'::character varying, 'tashkent_region'::character varying, 'andijon'::character varying, 'fergana'::character varying, 'namangan'::character varying, 'sirdaryo'::character varying, 'jizzax'::character varying, 'samarkand'::character varying, 'bukhara'::character varying, 'navoi'::character varying, 'kashkadarya'::character varying, 'surkhandarya'::character varying, 'khorezm'::character varying, 'karakalpakstan'::character varying])::text[])))
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: akt_documents id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.akt_documents ALTER COLUMN id SET DEFAULT nextval('public.akt_documents_id_seq'::regclass);


--
-- Name: akt_ratings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.akt_ratings ALTER COLUMN id SET DEFAULT nextval('public.akt_ratings_id_seq'::regclass);


--
-- Name: connection_orders id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.connection_orders ALTER COLUMN id SET DEFAULT nextval('public.connection_orders_id_seq'::regclass);


--
-- Name: connections id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.connections ALTER COLUMN id SET DEFAULT nextval('public.connections_id_seq'::regclass);


--
-- Name: material_and_technician id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_and_technician ALTER COLUMN id SET DEFAULT nextval('public.material_and_technician_id_seq'::regclass);


--
-- Name: material_issued id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_issued ALTER COLUMN id SET DEFAULT nextval('public.material_issued_id_seq'::regclass);


--
-- Name: material_requests id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_requests ALTER COLUMN id SET DEFAULT nextval('public.material_requests_id_seq'::regclass);


--
-- Name: materials id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.materials ALTER COLUMN id SET DEFAULT nextval('public.materials_id_seq'::regclass);


--
-- Name: media_files id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.media_files ALTER COLUMN id SET DEFAULT nextval('public.media_files_id_seq'::regclass);


--
-- Name: reports id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reports ALTER COLUMN id SET DEFAULT nextval('public.reports_id_seq'::regclass);


--
-- Name: smart_service_orders id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.smart_service_orders ALTER COLUMN id SET DEFAULT nextval('public.smart_service_orders_id_seq'::regclass);


--
-- Name: staff_orders id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff_orders ALTER COLUMN id SET DEFAULT nextval('public.staff_orders_id_seq'::regclass);


--
-- Name: tarif id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tarif ALTER COLUMN id SET DEFAULT nextval('public.tarif_id_seq'::regclass);


--
-- Name: technician_orders id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.technician_orders ALTER COLUMN id SET DEFAULT nextval('public.technician_orders_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: akt_documents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.akt_documents (id, request_id, request_type, akt_number, file_path, file_hash, sent_to_client_at, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: akt_ratings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.akt_ratings (id, request_id, request_type, rating, comment, created_at, updated_at) FROM stdin;
1	1	technician	3	\N	2025-10-10 02:18:35.930956+05	2025-10-10 02:18:35.930956+05
\.


--
-- Data for Name: connection_orders; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.connection_orders (id, application_number, user_id, region, address, tarif_id, business_type, longitude, latitude, jm_notes, cancellation_note, is_active, status, created_at, updated_at, diagnostics) FROM stdin;
\.


--
-- Data for Name: connections; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.connections (id, sender_id, recipient_id, connection_id, technician_id, staff_id, sender_status, recipient_status, created_at, updated_at) FROM stdin;
1	5	3	\N	1	\N	in_controller	in_technician	2025-10-10 01:27:23.289716+05	2025-10-10 01:27:23.289716+05
2	3	3	\N	1	\N	in_technician	in_technician_work	2025-10-10 01:36:31.930967+05	2025-10-10 01:36:31.930967+05
3	5	3	\N	1	\N	in_controller	in_technician	2025-10-10 01:43:25.334421+05	2025-10-10 01:43:25.334421+05
4	3	3	\N	1	\N	in_technician	in_technician_work	2025-10-10 01:44:51.928331+05	2025-10-10 01:44:51.928331+05
5	3	3	\N	1	\N	in_technician	in_technician_work	2025-10-10 01:46:59.326377+05	2025-10-10 01:46:59.326377+05
6	3	3	\N	1	\N	between_controller_technician	in_technician	2025-10-10 01:49:50.516305+05	2025-10-10 01:49:50.516305+05
7	3	3	\N	1	\N	in_technician	in_technician_work	2025-10-10 01:50:02.118915+05	2025-10-10 01:50:02.118915+05
8	3	3	\N	1	\N	between_controller_technician	in_technician	2025-10-10 02:04:14.519238+05	2025-10-10 02:04:14.519238+05
9	3	3	\N	1	\N	in_technician	in_technician_work	2025-10-10 02:04:24.883277+05	2025-10-10 02:04:24.883277+05
10	3	3	\N	1	\N	between_controller_technician	in_technician	2025-10-10 02:16:25.813195+05	2025-10-10 02:16:25.813195+05
11	3	3	\N	1	\N	in_technician	in_technician_work	2025-10-10 02:16:34.746782+05	2025-10-10 02:16:34.746782+05
12	3	3	\N	1	\N	in_technician_work	completed	2025-10-10 02:17:38.708431+05	2025-10-10 02:17:38.708431+05
13	5	3	\N	2	\N	in_controller	between_controller_technician	2025-10-10 02:35:35.934473+05	2025-10-10 02:35:35.934473+05
14	3	3	\N	2	\N	between_controller_technician	in_technician	2025-10-10 02:36:08.656425+05	2025-10-10 02:36:08.656425+05
15	3	3	\N	2	\N	in_technician	in_technician_work	2025-10-10 02:36:21.475961+05	2025-10-10 02:36:21.475961+05
16	3	2	\N	2	\N	in_technician_work	pending_warehouse	2025-10-10 02:38:19.630293+05	2025-10-10 02:38:19.630293+05
\.


--
-- Data for Name: material_and_technician; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.material_and_technician (id, user_id, material_id, quantity, created_at, updated_at) FROM stdin;
2	3	3	100	2025-10-10 01:35:32.38766+05	2025-10-10 01:35:32.38766+05
3	3	1	35	2025-10-10 01:35:50.544686+05	2025-10-10 01:35:50.544686+05
1	3	6	8	2025-10-10 01:35:19.867019+05	2025-10-10 02:37:01.212868+05
4	4	9	2	2025-10-10 03:14:38.660671+05	2025-10-10 03:14:38.660671+05
5	4	10	3	2025-10-10 03:14:38.680722+05	2025-10-10 03:14:38.680722+05
\.


--
-- Data for Name: material_issued; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.material_issued (id, material_id, quantity, price, total_price, issued_by, issued_at, material_name, material_unit, is_approved, application_number, request_type, created_at, updated_at) FROM stdin;
1	6	1	180000.00	180000.00	3	2025-10-10 02:17:38.612738+05	Modem (ADSL)	dona	f	TECH-B2C-0001	technician	2025-10-10 02:17:38.612738+05	2025-10-10 02:17:38.612738+05
\.


--
-- Data for Name: material_requests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.material_requests (id, description, user_id, applications_id, material_id, connection_order_id, technician_order_id, staff_order_id, quantity, price, total_price, source_type, warehouse_approved, created_at, updated_at) FROM stdin;
1	\N	3	1	6	\N	\N	\N	1	180000	180000	technician_stock	f	2025-10-10 02:17:17.159941+05	2025-10-10 02:17:17.159941+05
3	\N	3	2	9	\N	\N	\N	2	200	400	warehouse	t	2025-10-10 02:37:33.23833+05	2025-10-10 03:14:38.679112+05
4	\N	3	2	10	\N	\N	\N	3	35000	105000	warehouse	t	2025-10-10 02:38:06.156029+05	2025-10-10 03:14:38.682269+05
2	\N	3	2	6	\N	\N	\N	1	180000	180000	technician_stock	t	2025-10-10 02:37:01.212868+05	2025-10-10 03:14:38.68269+05
\.


--
-- Data for Name: materials; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.materials (id, name, price, description, quantity, serial_number, created_at, updated_at) FROM stdin;
2	WiFi router (TP-Link)	250000	Kuchli WiFi signal beruvchi router	25	TPL-001	2025-10-10 01:34:41.968744+05	2025-10-10 01:34:41.968744+05
4	RJ45 konnektor	500	Ethernet kabel uchun konnektor	500	RJ45-001	2025-10-10 01:34:41.968744+05	2025-10-10 01:34:41.968744+05
5	Kabel kanal (plastik)	8000	Kabellarni yashirish uchun	150	KANAL-001	2025-10-10 01:34:41.968744+05	2025-10-10 01:34:41.968744+05
7	Antenna (WiFi)	45000	WiFi signal kuchaytirish uchun	30	ANT-001	2025-10-10 01:34:41.968744+05	2025-10-10 01:34:41.968744+05
8	Splitter (internet)	12000	Internet va telefon uchun ajratgich	80	SPL-001	2025-10-10 01:34:41.968744+05	2025-10-10 01:34:41.968744+05
6	Modem (ADSL)	180000	Telefon liniyasi orqali internet	5	ADSL-001	2025-10-10 01:34:41.968744+05	2025-10-10 01:35:19.867019+05
3	Optik kabel (Fiber)	25000	Optik internet ulanish uchun	100	FIBER-001	2025-10-10 01:34:41.968744+05	2025-10-10 01:35:32.38766+05
1	Ethernet kabel (CAT6)	15000	Yuqori tezlikdagi internet ulanish uchun	65	CAT6-001	2025-10-10 01:34:41.968744+05	2025-10-10 01:35:50.544686+05
9	Kabel qisqich	200	Kabellarni mahkamlash uchun	998	QISQ-001	2025-10-10 01:34:41.968744+05	2025-10-10 03:14:38.67431+05
10	Power adapter (12V)	35000	Router va modem uchun quvvat	37	PWR-001	2025-10-10 01:34:41.968744+05	2025-10-10 03:14:38.681755+05
\.


--
-- Data for Name: media_files; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.media_files (id, file_path, file_type, file_size, original_name, mime_type, category, related_table, related_id, uploaded_by, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: reports; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.reports (id, title, description, created_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: smart_service_orders; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.smart_service_orders (id, application_number, user_id, category, service_type, address, longitude, latitude, is_active, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: staff_orders; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.staff_orders (id, application_number, user_id, phone, region, abonent_id, tarif_id, address, description, problem_description, diagnostics, jm_notes, cancellation_note, business_type, status, type_of_zayavka, is_active, created_by_role, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: tarif; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tarif (id, name, picture, created_at, updated_at) FROM stdin;
1	Hammasi birga 4	\N	2025-10-10 01:18:46.603818+05	2025-10-10 01:18:46.603818+05
2	Hammasi birga 3+	\N	2025-10-10 01:18:46.604796+05	2025-10-10 01:18:46.604796+05
3	Hammasi birga 3	\N	2025-10-10 01:18:46.605338+05	2025-10-10 01:18:46.605338+05
4	Hammasi birga 2	\N	2025-10-10 01:18:46.605965+05	2025-10-10 01:18:46.605965+05
\.


--
-- Data for Name: technician_orders; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.technician_orders (id, application_number, user_id, region, abonent_id, address, media, business_type, longitude, latitude, description, description_ish, description_operator, cancellation_note, status, is_active, created_at, updated_at) FROM stdin;
1	TECH-B2C-0001	4	sirdaryo	22222	Nimadir	AgACAgIAAxkBAAIfbGjoGhN0z5qqsAbhzdi7bXENyr6wAAJS_TEbQDRBS1szMK2x-WRqAQADAgADeQADNgQ	B2C	\N	\N	Muammo	dsfdfdsfasdds	\N	\N	completed	t	2025-10-10 01:26:31.638127+05	2025-10-10 02:17:38.708431+05
2	TECH-B2B-0001	4	tashkent_city	Uvvurruvruv	Bf7ubfff7	\N	B2B	\N	\N	Bfuf ubffi	afsdkhfasfhak	\N	\N	in_technician_work	t	2025-10-10 02:20:18.583496+05	2025-10-10 02:36:36.381309+05
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, telegram_id, full_name, username, phone, language, region, address, role, abonent_id, is_blocked, created_at, updated_at) FROM stdin;
1	\N	System Administrator	admin	\N	uz	\N	\N	admin	\N	f	2025-10-10 01:18:46.60061+05	2025-10-10 01:18:46.60061+05
4	860141119	User	\N	998974630172	uz	\N	\N	client	\N	f	2025-10-10 01:21:49.661231+05	2025-10-10 01:21:55.385071+05
2	1978574076	Ulug'bek	ulugbekbb	+998900042544	uz	\N	\N	warehouse	\N	f	2025-10-10 01:19:59.551477+05	2025-10-10 01:23:23.527212+05
5	5955605892	Salom	gulsara_yakubjanova	998908103399	uz	\N	\N	controller	\N	f	2025-10-10 01:22:10.159896+05	2025-10-10 01:23:39.235206+05
3	2129817198	Bakirlai	bakirali_zokirov	+998908200120	uz	\N	\N	technician	\N	f	2025-10-10 01:20:20.425763+05	2025-10-10 01:23:53.301917+05
\.


--
-- Name: akt_documents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.akt_documents_id_seq', 1, false);


--
-- Name: akt_ratings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.akt_ratings_id_seq', 1, true);


--
-- Name: connection_orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.connection_orders_id_seq', 1, false);


--
-- Name: connections_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.connections_id_seq', 16, true);


--
-- Name: material_and_technician_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.material_and_technician_id_seq', 5, true);


--
-- Name: material_issued_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.material_issued_id_seq', 1, true);


--
-- Name: material_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.material_requests_id_seq', 4, true);


--
-- Name: materials_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.materials_id_seq', 10, true);


--
-- Name: media_files_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.media_files_id_seq', 1, false);


--
-- Name: reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.reports_id_seq', 1, false);


--
-- Name: smart_service_orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.smart_service_orders_id_seq', 1, false);


--
-- Name: staff_orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.staff_orders_id_seq', 1, false);


--
-- Name: tarif_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tarif_id_seq', 4, true);


--
-- Name: technician_orders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.technician_orders_id_seq', 2, true);


--
-- Name: user_sequential_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_sequential_id_seq', 6, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 5, true);


--
-- Name: akt_documents akt_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.akt_documents
    ADD CONSTRAINT akt_documents_pkey PRIMARY KEY (id);


--
-- Name: akt_ratings akt_ratings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.akt_ratings
    ADD CONSTRAINT akt_ratings_pkey PRIMARY KEY (id);


--
-- Name: connection_orders connection_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.connection_orders
    ADD CONSTRAINT connection_orders_pkey PRIMARY KEY (id);


--
-- Name: connections connections_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.connections
    ADD CONSTRAINT connections_pkey PRIMARY KEY (id);


--
-- Name: material_and_technician material_and_technician_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_and_technician
    ADD CONSTRAINT material_and_technician_pkey PRIMARY KEY (id);


--
-- Name: material_issued material_issued_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_issued
    ADD CONSTRAINT material_issued_pkey PRIMARY KEY (id);


--
-- Name: material_requests material_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_requests
    ADD CONSTRAINT material_requests_pkey PRIMARY KEY (id);


--
-- Name: materials materials_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT materials_pkey PRIMARY KEY (id);


--
-- Name: materials materials_serial_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.materials
    ADD CONSTRAINT materials_serial_number_key UNIQUE (serial_number);


--
-- Name: media_files media_files_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.media_files
    ADD CONSTRAINT media_files_pkey PRIMARY KEY (id);


--
-- Name: reports reports_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_pkey PRIMARY KEY (id);


--
-- Name: smart_service_orders smart_service_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.smart_service_orders
    ADD CONSTRAINT smart_service_orders_pkey PRIMARY KEY (id);


--
-- Name: staff_orders staff_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff_orders
    ADD CONSTRAINT staff_orders_pkey PRIMARY KEY (id);


--
-- Name: tarif tarif_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tarif
    ADD CONSTRAINT tarif_pkey PRIMARY KEY (id);


--
-- Name: technician_orders technician_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.technician_orders
    ADD CONSTRAINT technician_orders_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_telegram_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_telegram_id_key UNIQUE (telegram_id);


--
-- Name: material_and_technician ux_mat_tech_user_material; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_and_technician
    ADD CONSTRAINT ux_mat_tech_user_material UNIQUE (user_id, material_id);


--
-- Name: CONSTRAINT ux_mat_tech_user_material ON material_and_technician; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON CONSTRAINT ux_mat_tech_user_material ON public.material_and_technician IS 'Ensures unique combination of user_id and material_id for UPSERT operations';


--
-- Name: idx_connection_orders_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_connection_orders_created ON public.connection_orders USING btree (created_at);


--
-- Name: idx_connection_orders_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_connection_orders_status ON public.connection_orders USING btree (status);


--
-- Name: idx_connection_orders_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_connection_orders_user ON public.connection_orders USING btree (user_id);


--
-- Name: idx_connections_recipient; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_connections_recipient ON public.connections USING btree (recipient_id);


--
-- Name: idx_connections_sender; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_connections_sender ON public.connections USING btree (sender_id);


--
-- Name: idx_materials_serial; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_materials_serial ON public.materials USING btree (serial_number);


--
-- Name: idx_media_files_related; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_media_files_related ON public.media_files USING btree (related_table, related_id);


--
-- Name: idx_sso_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sso_category ON public.smart_service_orders USING btree (category);


--
-- Name: idx_sso_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sso_user_id ON public.smart_service_orders USING btree (user_id);


--
-- Name: idx_staff_orders_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_staff_orders_status ON public.staff_orders USING btree (status);


--
-- Name: idx_staff_orders_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_staff_orders_user ON public.staff_orders USING btree (user_id);


--
-- Name: idx_technician_orders_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_technician_orders_created ON public.technician_orders USING btree (created_at);


--
-- Name: idx_technician_orders_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_technician_orders_status ON public.technician_orders USING btree (status);


--
-- Name: idx_technician_orders_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_technician_orders_user ON public.technician_orders USING btree (user_id);


--
-- Name: idx_users_abonent_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_abonent_id ON public.users USING btree (abonent_id);


--
-- Name: idx_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_id ON public.users USING btree (id);


--
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_role ON public.users USING btree (role);


--
-- Name: akt_documents trg_akt_documents_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_akt_documents_updated_at BEFORE UPDATE ON public.akt_documents FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: akt_ratings trg_akt_ratings_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_akt_ratings_updated_at BEFORE UPDATE ON public.akt_ratings FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: connection_orders trg_connection_orders_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_connection_orders_updated_at BEFORE UPDATE ON public.connection_orders FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: material_and_technician trg_material_and_technician_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_material_and_technician_updated_at BEFORE UPDATE ON public.material_and_technician FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: material_issued trg_material_issued_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_material_issued_updated_at BEFORE UPDATE ON public.material_issued FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: material_requests trg_material_requests_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_material_requests_updated_at BEFORE UPDATE ON public.material_requests FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: materials trg_materials_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_materials_updated_at BEFORE UPDATE ON public.materials FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: media_files trg_media_files_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_media_files_updated_at BEFORE UPDATE ON public.media_files FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: reports trg_reports_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_reports_updated_at BEFORE UPDATE ON public.reports FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: smart_service_orders trg_sso_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_sso_updated_at BEFORE UPDATE ON public.smart_service_orders FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: staff_orders trg_staff_orders_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_staff_orders_updated_at BEFORE UPDATE ON public.staff_orders FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: tarif trg_tarif_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_tarif_updated_at BEFORE UPDATE ON public.tarif FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: technician_orders trg_technician_orders_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_technician_orders_updated_at BEFORE UPDATE ON public.technician_orders FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: users trg_users_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: connection_orders connection_orders_tarif_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.connection_orders
    ADD CONSTRAINT connection_orders_tarif_id_fkey FOREIGN KEY (tarif_id) REFERENCES public.tarif(id) ON DELETE SET NULL;


--
-- Name: connection_orders connection_orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.connection_orders
    ADD CONSTRAINT connection_orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: connections connections_connection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.connections
    ADD CONSTRAINT connections_connection_id_fkey FOREIGN KEY (connection_id) REFERENCES public.connection_orders(id) ON DELETE SET NULL;


--
-- Name: connections connections_recipient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.connections
    ADD CONSTRAINT connections_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: connections connections_sender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.connections
    ADD CONSTRAINT connections_sender_id_fkey FOREIGN KEY (sender_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: connections connections_staff_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.connections
    ADD CONSTRAINT connections_staff_id_fkey FOREIGN KEY (staff_id) REFERENCES public.staff_orders(id) ON DELETE SET NULL;


--
-- Name: connections connections_technician_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.connections
    ADD CONSTRAINT connections_technician_id_fkey FOREIGN KEY (technician_id) REFERENCES public.technician_orders(id) ON DELETE SET NULL;


--
-- Name: material_and_technician material_and_technician_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_and_technician
    ADD CONSTRAINT material_and_technician_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE SET NULL;


--
-- Name: material_and_technician material_and_technician_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_and_technician
    ADD CONSTRAINT material_and_technician_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: material_issued material_issued_issued_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_issued
    ADD CONSTRAINT material_issued_issued_by_fkey FOREIGN KEY (issued_by) REFERENCES public.users(id);


--
-- Name: material_issued material_issued_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_issued
    ADD CONSTRAINT material_issued_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE RESTRICT;


--
-- Name: material_requests material_requests_connection_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_requests
    ADD CONSTRAINT material_requests_connection_order_id_fkey FOREIGN KEY (connection_order_id) REFERENCES public.connection_orders(id) ON DELETE SET NULL;


--
-- Name: material_requests material_requests_material_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_requests
    ADD CONSTRAINT material_requests_material_id_fkey FOREIGN KEY (material_id) REFERENCES public.materials(id) ON DELETE SET NULL;


--
-- Name: material_requests material_requests_staff_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_requests
    ADD CONSTRAINT material_requests_staff_order_id_fkey FOREIGN KEY (staff_order_id) REFERENCES public.staff_orders(id) ON DELETE SET NULL;


--
-- Name: material_requests material_requests_technician_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_requests
    ADD CONSTRAINT material_requests_technician_order_id_fkey FOREIGN KEY (technician_order_id) REFERENCES public.technician_orders(id) ON DELETE SET NULL;


--
-- Name: material_requests material_requests_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_requests
    ADD CONSTRAINT material_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: media_files media_files_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.media_files
    ADD CONSTRAINT media_files_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: reports reports_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT reports_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: smart_service_orders smart_service_orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.smart_service_orders
    ADD CONSTRAINT smart_service_orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: staff_orders staff_orders_tarif_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff_orders
    ADD CONSTRAINT staff_orders_tarif_id_fkey FOREIGN KEY (tarif_id) REFERENCES public.tarif(id) ON DELETE SET NULL;


--
-- Name: staff_orders staff_orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.staff_orders
    ADD CONSTRAINT staff_orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: technician_orders technician_orders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.technician_orders
    ADD CONSTRAINT technician_orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

