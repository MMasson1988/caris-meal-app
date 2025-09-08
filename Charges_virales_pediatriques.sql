use caris_db;

SELECT 
    b.*, a.*
FROM
    (SELECT 
        IF(lh.id IS NOT NULL, CONCAT(lh.city_code, '/', lh.hospital_code), CONCAT(pt.city_code, '/', pt.hospital_code)) AS site,
            IF(lh.id IS NOT NULL, lh.name, lh2.name) AS hospital_name,
            IF(lh.id IS NOT NULL, lh.id, lh2.id) AS id_hospital,
            pt.patient_code,
            a.*,
            carer_name,
            carer_address,
            carer_telephone,
            ti.in_dots,
            ti.dots_facilitator,
            ti.schooling_program,
            ti.education_program,
            ti.gardening_program,
            COALESCE(location, gps, '') gps,
            IF(ti.gender = 1, 'M', IF(ti.gender = 2, 'F', ti.gender)) AS sex,
            ti.dob AS date_of_birth,
            ti.is_abandoned,
            ti.is_dead,
            ti.first_name,
            ti.last_name,
            IF(cb.id_patient IS NULL, 'NO', 'YES') AS in_club,
            CASE
                WHEN cb.club_type = 2 THEN 'club_9_12'
                WHEN cb.club_type = 3 THEN 'club_13_17'
                WHEN cb.club_type = 4 THEN 'club_18+'
                WHEN cb.club_type = 5 THEN 'club_3_5'
                WHEN cb.club_type = 6 THEN 'club_6_8'
                ELSE 'not_in_club'
            END AS club_type,
            b.took_viral_load_test,
            b.viral_load_indetectable,
            b.viral_load_count,
            b1.viral_load_count AS prev_viral_load_count,
            last_viral_load_collection_date,
            inh_initiation_date,
            inh_completion_date,
            IF((b.viral_load_indetectable
                OR b.viral_load_count < 1000), 'OUI', IF(b.viral_load_count >= 1000, 'NON', b.viral_load_count)) AS indetectable_ou_inf_1000,
            arv.start_date AS arv_start_date,
            arv.regime,
            arv.all_start_date AS all_arv_start_date,
            arv.all_end_date AS all_arv_end_date,
            actual_arv.regime AS actual_arv_regime,
            b1.viral_load_date AS prev_viral_load_date,
            b.viral_load_date,
            IF((b.viral_load_indetectable
                OR b.viral_load_count < 1000), DATE_ADD(b.viral_load_date, INTERVAL 1 YEAR), IF(b.viral_load_count >= 1000, DATE_ADD(b.viral_load_date, INTERVAL 6 MONTH), 'on ne sait pas')) AS next_viral_load_date,
            IF(((b.took_viral_load_test IS NULL)
                OR b.took_viral_load_test = 0), IF(((TIMESTAMPDIFF(MONTH, arv.start_date, NOW()) < 6)
                OR (arv.start_date IS NULL)), 'NO', 'YES'), IF(((b.viral_load_indetectable
                OR b.viral_load_count < 1000)
                AND DATE_ADD(b.viral_load_date, INTERVAL 1 YEAR) < NOW())
                OR (b.viral_load_count >= 1000
                AND DATE_ADD(b.viral_load_date, INTERVAL 6 MONTH) < NOW()), 'YES', 'NO')) AS eligibility,
            c.last_session_date,
            IF(c.last_session_date + INTERVAL 12 MONTH > NOW(), 'yes', 'no') AS is_actually_in_club,
            TIMESTAMPDIFF(YEAR, ti.dob, NOW()) AS age,
            IF(TIMESTAMPDIFF(YEAR, ti.dob, NOW()) BETWEEN 9 AND 12, 'OUI', 'NON') AS '9-12',
            IF(TIMESTAMPDIFF(YEAR, ti.dob, NOW()) BETWEEN 13 AND 17, 'OUI', 'NON') AS '13-17',
            IF(TIMESTAMPDIFF(YEAR, ti.dob, NOW()) >= 18, 'OUI', 'NON') AS '18+',
            tf.date AS last_followup_date,
            tf.next_appointment_date,
            CASE
                WHEN TIMESTAMPDIFF(DAY, tf.date, next_appointment_date) <= 35 THEN 'MMS_0_35'
                WHEN
                    TIMESTAMPDIFF(DAY, tf.date, next_appointment_date) >= 36
                        AND TIMESTAMPDIFF(DAY, tf.date, next_appointment_date) <= 89
                THEN
                    'MMS_36_89'
                WHEN
                    TIMESTAMPDIFF(DAY, tf.date, next_appointment_date) >= 90
                        AND TIMESTAMPDIFF(DAY, tf.date, next_appointment_date) <= 120
                THEN
                    'MMS_90_120'
                WHEN
                    TIMESTAMPDIFF(DAY, tf.date, next_appointment_date) >= 121
                        AND TIMESTAMPDIFF(DAY, tf.date, next_appointment_date) <= 180
                THEN
                    'MMS_121_180'
                ELSE 'MMS_>_180'
            END AS MMS,
            IF(TIMESTAMPDIFF(MONTH, tf.next_appointment_date, NOW()) > 6, 'Yes', 'No') AS 'LTFU 6months',
            IF(TIMESTAMPDIFF(MONTH, tf.next_appointment_date, NOW()) > 12, 'Yes', 'No') AS 'LTFU_1year',
            IF(TIMESTAMPDIFF(DAY, tf.next_appointment_date, NOW()) > 30, 'Yes', 'No') AS 'LTFU 30days',
            IF(TIMESTAMPDIFF(MONTH, tf.next_appointment_date, NOW()) >= 1
                AND TIMESTAMPDIFF(MONTH, tf.next_appointment_date, NOW()) < 6, 'Yes', 'No') AS 'LTFU_1month_inf_6months',
            IF(TIMESTAMPDIFF(MONTH, tf.next_appointment_date, NOW()) >= 6
                AND TIMESTAMPDIFF(MONTH, tf.next_appointment_date, NOW()) < 12, 'Yes', 'No') AS 'LTFU_6_inf12months',
            IF(TIMESTAMPDIFF(MONTH, tf.next_appointment_date, NOW()) > 12, 'Yes', 'No') AS 'LTFU_12months_plus',
            IF(pcr.id_patient IS NULL, 'No', 'Yes') AS is_positive_by_pcr,
            wh.weight,
            wh.date AS weight_date,
            ln.name AS network,
            IF(ugp.id IS NOT NULL, 'Yes', 'No') AS is_ugp,
            lhl.office
    FROM
        (SELECT 
        id AS id_patient
    FROM
        view_patient_positive UNION (SELECT 
        id_patient
    FROM
        tracking_regime t_reg
    WHERE
        t_reg.category = 'regime_infant_treatment') UNION (SELECT 
        id_patient
    FROM
        club_patient cp
    LEFT JOIN club c ON c.id = cp.id_club
    WHERE
        c.club_type != 1)) a
    LEFT JOIN (SELECT 
        id_patient, name AS club_name, club_type
    FROM
        club_patient cp
    LEFT JOIN club c ON c.id = cp.id_club
    WHERE
        c.club_type != 1) cb ON a.id_patient = cb.id_patient
    LEFT JOIN tracking_infant ti ON ti.id_patient = a.id_patient
    LEFT JOIN lookup_hospital lh ON lh.id = ti.id_hospital
    LEFT JOIN (SELECT 
        id,
            id_patient,
            took_viral_load_test,
            viral_load_indetectable,
            viral_load_count,
            viral_load_date
    FROM
        tracking_followup tf1
    WHERE
        took_viral_load_test
            AND tf1.viral_load_date = (SELECT 
                MAX(tf2.viral_load_date)
            FROM
                tracking_followup tf2
            WHERE
                tf1.id_patient = tf2.id_patient)
    GROUP BY tf1.id_patient) b ON b.id_patient = a.id_patient
    LEFT JOIN (SELECT 
        id,
            id_patient,
            took_viral_load_test,
            viral_load_indetectable,
            viral_load_count,
            viral_load_date
    FROM
        tracking_followup tf1
    WHERE
        took_viral_load_test
            AND tf1.viral_load_date = (SELECT 
                MAX(tf2.viral_load_date)
            FROM
                tracking_followup tf2
            WHERE
                tf1.id_patient = tf2.id_patient
                    AND tf2.viral_load_date < (SELECT 
                        MAX(tf3.viral_load_date)
                    FROM
                        tracking_followup tf3
                    WHERE
                        tf3.id_patient = tf1.id_patient))
    GROUP BY tf1.id_patient) b1 ON b1.id_patient = a.id_patient
    LEFT JOIN (SELECT 
        patient.id, odk_child_visit.patient_code, location, gps
    FROM
        openfn.odk_child_visit
    LEFT JOIN patient ON patient.patient_code = odk_child_visit.patient_code
    WHERE
        location IS NOT NULL OR gps != ''
    GROUP BY odk_child_visit.patient_code) odk ON odk.id = a.id_patient
    LEFT JOIN (SELECT 
        id_patient,
            inh_eligibility,
            is_on_inh,
            inh_initiation_date,
            inh_length,
            is_inh_completed,
            inh_completion_date
    FROM
        tracking_followup t1
    WHERE
        inh_eligibility
            AND inh_initiation_date IS NOT NULL
    GROUP BY t1.id_patient) inh ON a.id_patient = inh.id_patient
    LEFT JOIN (SELECT 
        ss.id_patient,
            ss.is_present,
            MAX(cs.date) AS last_session_date
    FROM
        (SELECT 
        id_patient, id_club_session, is_present
    FROM
        session
    WHERE
        is_present = 1 AND id_patient) ss
    LEFT JOIN club_session cs ON ss.id_club_session = cs.id
    GROUP BY ss.id_patient) c ON c.id_patient = a.id_patient
    LEFT JOIN (SELECT 
        id_patient,
            MIN(IF(start_date != '0000-00-00', start_date, NULL)) AS start_date,
            GROUP_CONCAT(la.acronym
                SEPARATOR '-') AS regime,
            GROUP_CONCAT(tr.start_date
                SEPARATOR ' | ') AS all_start_date,
            GROUP_CONCAT(tr.end_date
                SEPARATOR ' | ') AS all_end_date
    FROM
        tracking_regime tr
    LEFT JOIN lookup_arv la ON la.id = tr.id_arv
    WHERE
        category = 'regime_infant_treatment'
    GROUP BY id_patient) arv ON arv.id_patient = a.id_patient
    LEFT JOIN (SELECT 
        id_patient,
            MIN(IF(start_date != '0000-00-00', start_date, NULL)) AS start_date,
            GROUP_CONCAT(la.acronym
                SEPARATOR '-') AS regime,
            GROUP_CONCAT(tr.start_date
                SEPARATOR ' | ') AS all_start_date,
            GROUP_CONCAT(tr.end_date
                SEPARATOR ' | ') AS all_end_date
    FROM
        tracking_regime tr
    LEFT JOIN lookup_arv la ON la.id = tr.id_arv
    WHERE
        category = 'regime_infant_treatment'
            AND (tr.end_date = '0000-00-00'
            OR (tr.end_date IS NULL))
    GROUP BY id_patient) actual_arv ON actual_arv.id_patient = a.id_patient
    LEFT JOIN (SELECT 
        tf1.id_patient, tf1.date, tf1.next_appointment_date
    FROM
        tracking_followup tf1
    WHERE
        tf1.date = (SELECT 
                MAX(tf2.date)
            FROM
                tracking_followup tf2
            WHERE
                tf1.id_patient = tf2.id_patient)
    GROUP BY tf1.id_patient) tf ON tf.id_patient = a.id_patient
    LEFT JOIN patient pt ON pt.id = a.id_patient
    LEFT JOIN lookup_hospital lh2 ON CONCAT(lh2.city_code, '/', lh2.hospital_code) = CONCAT(pt.city_code, '/', pt.hospital_code)
    LEFT JOIN (SELECT 
        id_patient
    FROM
        tracking_motherbasicinfo) tm ON tm.id_patient = a.id_patient
    LEFT JOIN ((SELECT 
        id_patient
    FROM
        testing_specimen
    WHERE
        pcr_result = 1) UNION (SELECT 
        id_patient
    FROM
        testing_result
    WHERE
        result = 1)) pcr ON pcr.id_patient = a.id_patient
    LEFT JOIN (SELECT 
        id_patient, tf1.weight, tf1.date
    FROM
        tracking_followup tf1
    WHERE
        tf1.weight > 0
            AND tf1.date = (SELECT 
                MAX(tf2.date)
            FROM
                tracking_followup tf2
            WHERE
                tf2.id_patient = tf1.id_patient
                    AND tf2.weight > 0)
    GROUP BY tf1.id_patient) wh ON wh.id_patient = a.id_patient
    LEFT JOIN (SELECT 
        tf.id_patient,
            MAX(tf.viral_load_collection_date) AS last_viral_load_collection_date
    FROM
        tracking_followup tf
    WHERE
        viral_load_collection_date != '0000-00-00'
            AND (viral_load_collection_date IS NOT NULL)
    GROUP BY id_patient) vcd ON vcd.id_patient = a.id_patient
    LEFT JOIN lookup_hospital lhl ON CONCAT(lhl.city_code, '/', lhl.hospital_code) = IF(lh.id IS NOT NULL, CONCAT(lh.city_code, '/', lh.hospital_code), CONCAT(pt.city_code, '/', pt.hospital_code))
    LEFT JOIN lookup_network ln ON ln.id = lhl.network
    LEFT JOIN hospital_network ugp ON ugp.id_hospital = lhl.id
        AND ugp.id_network = 7
    WHERE
        (ti.is_dead != 1 OR (ti.is_dead IS NULL))
            AND (pt.linked_to_id_patient = 0)
            AND (tm.id_patient IS NULL)
    ORDER BY IF(lh.id IS NOT NULL, CONCAT(lh.city_code, '/', lh.hospital_code), CONCAT(pt.city_code, '/', pt.hospital_code))) a
        LEFT JOIN
    (SELECT 
        ld.name AS departement,
            lc.name AS commune,
            ls.name AS section,
            CONCAT(lh.city_code, '/', lh.hospital_code) AS site,
            lh.name AS hospital_name
    FROM
        lookup_hospital lh
    LEFT JOIN lookup_section ls ON ls.id = lh.section
    LEFT JOIN lookup_commune lc ON lc.id = lh.commune
    LEFT JOIN lookup_departement ld ON ld.id = lc.departement
    LEFT JOIN lookup_network ln ON ln.id = lh.network) b ON a.site = b.site
    HAVING NOT (departement IN ('Nippes' , 'Sud', 'Sud-Est', 'Grand-Anse')
        OR office IN ('JER' , 'CAY', 'FDN', 'MIR'))

