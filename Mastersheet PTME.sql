SELECT
    b.office,
    b.network,
    b.departement,
    b.commune,
    b.section,
    b.hospital_name,
    h.*,
    v.*,
	group_concat(
			CASE
				WHEN h.why_this_woman_does_not_belong_to_a_club = 1 THEN 'N\ ’était pas au courant du club'
				WHEN h.why_this_woman_does_not_belong_to_a_club = 2 THEN 'Distance/Proximité (clubs trop loin)'
				WHEN h.why_this_woman_does_not_belong_to_a_club = 3 THEN 'Incompatibilité d\ ’horaire'
				WHEN h.why_this_woman_does_not_belong_to_a_club = 4 THEN 'Raison économique'
				WHEN h.why_this_woman_does_not_belong_to_a_club = 5 THEN 'Stigmatisation'
				WHEN h.why_this_woman_does_not_belong_to_a_club = 6 THEN 'Dénie (n\ ’accepte pas son statut)'
				WHEN h.why_this_woman_does_not_belong_to_a_club = 7 THEN 'Partenaire n’est pas au courant de son statut'
				WHEN h.why_this_woman_does_not_belong_to_a_club = 8 THEN 'Autres'
				ELSE h.why_this_woman_does_not_belong_to_a_club
			END )AS woman_does_not_belong_to_a_club_definition ,
    IF(h.actual_delivery_date != '0000-00-00'
            AND (h.actual_delivery_date IS NOT NULL),
        h.actual_delivery_date,
        GREATEST(COALESCE(h.infant_dob, 0),
                COALESCE(v.date_of_delivery_commcare, 0))) AS delivery_date_merge,
    IF(h.actual_delivery_date != '0000-00-00'
            AND (h.actual_delivery_date IS NOT NULL),
        h.actual_delivery_date,
        GREATEST(COALESCE(h.infant_dob, 0),
                COALESCE(v.date_of_delivery_commcare, 0),
                COALESCE(h.dpa, 0),
                COALESCE(h.ddr + INTERVAL 9 MONTH + INTERVAL 7 DAY,
                        0))) AS delivery_probality_date_merge,
    h.ddr + INTERVAL 9 MONTH + INTERVAL 7 DAY AS DPA_calculated,
    IF(TIMESTAMPDIFF(MONTH,
            h.infant_dob,
            NOW()) < 24,
        'yes',
        IF(h.termination_of_pregnancy = 1,
            'no',
            IF(TIMESTAMPDIFF(MONTH,
                    IF(h.actual_delivery_date != '0000-00-00'
                            AND (h.actual_delivery_date IS NOT NULL),
                        h.actual_delivery_date,
                        GREATEST(COALESCE(h.infant_dob, 0),
                                COALESCE(v.date_of_delivery_commcare, 0))),
                    NOW()) < 24,
                'yes',
                'no'))) AS allaitante,
    IF( (!( h.actual_delivery_date BETWEEN (NOW() - INTERVAL 5 MONTH) AND NOW())) AND (h.termination_of_pregnancy is null or h.termination_of_pregnancy!=1),
        IF(TIMESTAMPDIFF(MONTH, h.ddr, NOW()) < 9
                OR IF(h.actual_delivery_date != '0000-00-00'
                    AND (h.actual_delivery_date IS NOT NULL),
                h.actual_delivery_date,
                GREATEST(COALESCE(h.infant_dob, 0),
                        COALESCE(h.dpa, 0),
                        COALESCE(h.ddr + INTERVAL 9 MONTH + INTERVAL 7 DAY,
                                0))) > NOW(),
            'yes',
            'no'),
        'no') AS enceinte,
    IF( (!( h.actual_delivery_date BETWEEN (NOW() - INTERVAL 5 MONTH) AND NOW())) AND (h.termination_of_pregnancy is null or h.termination_of_pregnancy!=1),
        IF(TIMESTAMPDIFF(MONTH, h.ddr, NOW()) < 9
                OR IF(h.actual_delivery_date != '0000-00-00'
                    AND (h.actual_delivery_date IS NOT NULL),
                h.actual_delivery_date,
                GREATEST(COALESCE(h.infant_dob, 0),
                        COALESCE(h.dpa, 0),
                        COALESCE(h.ddr + INTERVAL 9 MONTH + INTERVAL 7 DAY,
                                0))) between (NOW() - INTERVAL 7 DAY) AND NOW(),
            'yes',
            'no'),
        'no') AS enceinte_bt_7_14,
        tf.last_followup_date,
        tf.next_appointment_date
FROM
    (SELECT 
        a.id_patient,
            p.patient_code AS mother_patient_code,
            p.created_at,
            LEFT(p.patient_code, 8) AS site,
            tmi.first_name AS first_name,
            tmi.last_name AS last_name,
            tmi.dob,
            TIMESTAMPDIFF(YEAR, tmi.dob, NOW()) AS age,
            tmi.address,
            nt.name AS Hospital,
            IF(nt.id_network = 7, 'UGP', IF(nt.network = 6, 'SANTE', 'autres')) AS network_name,
            IF(tmi.is_MUSO = 0, 'No', 'Yes') AS Muso_program,
            IF(tmi.gardening_program = 0, 'No', 'Yes') AS gardening_program,
            IF(tmi.psy_program = 0, 'No', 'Yes') AS Psy_program,
            IF(tmi.DREAMS_program = 0, 'No', 'Yes') AS Dreams_program,
            IF(tmi.nutrition_program = 0, 'No', 'Yes') AS Nutrition_program,
            IF(tmi.schooling_program = 0, 'No', 'Yes') AS Schooling_program,
            IF(tmi.education_program = 0, 'No', 'Yes') AS Education_program,
            tmi.telephone AS telephone1,
            tmi.telephone2 AS Telephone2,
            tmi.is_PTME,
            tmi.PTME_date,
            tmi.is_abandoned,
            tmi.abandoned_reason,
            lar.name AS abandoned_reason_name,
            tmi.abandoned_reason_other_describe,
            tmi.comments,
            tmi.is_dead,
            tmi.is_address_incorrect,
            tmi.patient_doesnot_accept_visits,
            tmi.cervical_cancer_screening,
            tmi.cervical_cancer_screening_date,
            tmi.reference_for_cervical_cancer_screening,
            IF(cp.id_patient IS NOT NULL, 'yes', 'no') AS in_club,
            info_club.club_session_date AS club_session_date,
            IF(info_club.club_session_date + INTERVAL 12 MONTH > NOW(), 'yes', 'no') AS is_actually_in_club,
            info_club.club_name AS Club_name,
            tmi.why_this_woman_does_not_belong_to_a_club,
            this_woman_does_not_belong_to_a_club_reason_other,
            preg.termination_of_pregnancy,
            lrtp.name AS termination_of_pregnancy_reason,
            preg.on_arv AS on_arv_from_preg,
            preg.actual_delivery_date,
            preg.dpa,
            preg.ddr,
            preg.ptme_enrollment_date,
            preg.created_at AS pregnancy_created_at,
            IF(tme3.id_patient IS NOT NULL, 'yes', 'no') AS has_mereenfant_form,
            pch.patient_code AS child_patient_code,
            tme3.infant_dob,
            tme3.infant_prophylaxis_arv_regime,
            ltpx.name AS Prophylasis_regime,
            ltn.name AS infant_nutrition,
            ltb2.name AS infant_birth_location,
            tme3.infant_birth_location_describe,
            lr.name AS infant_prophylaxis_arv_regime_before_or_after,
            tme3.mother_enrolled_in_ptme,
            IF(arv.id_patient IS NOT NULL, 'yes', 'no') AS on_arv,
            IF(arv_infant.id_patient IS NOT NULL, 'yes', 'no') AS Arv_infant,
            sp.date_blood_taken,
            ltsr.name AS pcr_result,
            pcr_result_date,
            lrtw.name AS which_pcr,
            ti.is_abandoned AS Child_abandon,
            ti.is_dead AS child_dead
    FROM
        ((SELECT 
        tmi.id_patient
    FROM
        tracking_pregnancy tp
    LEFT JOIN tracking_motherbasicinfo tmi ON tmi.id_patient = tp.id_patient_mother
    WHERE
        (tp.dpa BETWEEN (NOW() - INTERVAL 24 MONTH) AND (NOW() + INTERVAL 9 MONTH))
            OR ((tp.ddr + INTERVAL 9 MONTH + INTERVAL 7 DAY) BETWEEN (NOW() - INTERVAL 24 MONTH) AND (NOW() + INTERVAL 9 MONTH))
            OR (tp.actual_delivery_date BETWEEN (NOW() - INTERVAL 24 MONTH) AND (NOW() + INTERVAL 9 MONTH))
            OR (tp.created_at BETWEEN NOW() AND NOW())
            OR (tmi.created_at BETWEEN NOW() AND NOW())) UNION (SELECT 
        p.id AS id_patient
    FROM
        testing_mereenfant tme
    LEFT JOIN patient p ON p.patient_code = CONCAT(tme.mother_city_code, '/', tme.mother_hospital_code, '/', tme.mother_code)
    WHERE
        tme.infant_dob BETWEEN (NOW() - INTERVAL 24 MONTH) AND (NOW() + INTERVAL 9 MONTH)) UNION (SELECT 
        id_patient_mother AS id_patient
    FROM
        tracking_children tc
    LEFT JOIN tracking_motherbasicinfo tmi2 ON tmi2.id_patient = tc.id_patient_mother
    LEFT JOIN testing_mereenfant tm ON tm.id_patient = tc.id_patient_child
    WHERE
        (tmi2.id IS NOT NULL)
            AND (tm.infant_dob BETWEEN (NOW() - INTERVAL 24 MONTH) AND (NOW() + INTERVAL 9 MONTH))
            OR (tc.dob BETWEEN (NOW() - INTERVAL 24 MONTH) AND (NOW() + INTERVAL 9 MONTH)))) a
    LEFT JOIN (SELECT 
        *
    FROM
        patient
    WHERE
        linked_to_id_patient = 0) p ON p.id = a.id_patient
    LEFT JOIN (SELECT 
        qm2.id_patient,
            qm2.date,
            qm2.infant_count_alive,
            qm2.infant_count
    FROM
        (SELECT 
        MAX(qm.date) AS last_date, qm.id_patient
    FROM
        questionnaire_mothersurvey qm
    WHERE
        (qm.infant_count_alive IS NOT NULL)
    GROUP BY qm.id_patient) q
    INNER JOIN questionnaire_mothersurvey qm2 ON qm2.id_patient = q.id_patient
        AND q.last_date = qm2.date) zx ON zx.id_patient = a.id_patient
    LEFT JOIN tracking_motherbasicinfo tmi ON tmi.id_patient = a.id_patient
    LEFT JOIN lookup_abandoned_reason lar ON lar.id = tmi.abandoned_reason
    LEFT JOIN (SELECT 
        *
    FROM
        tracking_pregnancy tp2
    WHERE
        (tp2.dpa BETWEEN (NOW() - INTERVAL 24 MONTH) AND (NOW() + INTERVAL 9 MONTH))
            OR ((tp2.ddr + INTERVAL 9 MONTH + INTERVAL 7 DAY) BETWEEN (NOW() - INTERVAL 24 MONTH) AND (NOW() + INTERVAL 9 MONTH))
            OR (tp2.actual_delivery_date BETWEEN (NOW() - INTERVAL 24 MONTH) AND (NOW() + INTERVAL 9 MONTH))
    GROUP BY tp2.id_patient_mother) preg ON preg.id_patient_mother = a.id_patient
    LEFT JOIN club_patient cp ON cp.id_patient = a.id_patient
    LEFT JOIN (SELECT DISTINCT
        club.name AS club_name,
            patient.id AS id_patient_club,
            patient_code,
            MAX(club_session.date) AS club_session_date
    FROM
        session
    LEFT JOIN club_session ON club_session.id = id_club_session
    LEFT JOIN club ON club.id = id_club
    LEFT JOIN patient ON patient.id = id_patient
    WHERE
        is_present = 1 AND club_type = 1
            AND LEFT(patient_code, 8) IS NOT NULL
    GROUP BY patient.id) info_club ON info_club.id_patient_club = a.id_patient
    LEFT JOIN ((SELECT 
        p.id AS id_patient_mother,
            tme2.id_patient AS id_patient_child
    FROM
        testing_mereenfant tme2
    LEFT JOIN patient p ON p.patient_code = CONCAT(tme2.mother_city_code, '/', tme2.mother_hospital_code, '/', tme2.mother_code)
    WHERE
        tme2.infant_dob BETWEEN (NOW() - INTERVAL 24 MONTH) AND (NOW() + INTERVAL 9 MONTH)) UNION (SELECT 
        id_patient_mother, id_patient_child
    FROM
        tracking_children tc
    LEFT JOIN testing_mereenfant tm ON tm.id_patient = tc.id_patient_child
    LEFT JOIN tracking_motherbasicinfo tmi1 ON tmi1.id_patient = tc.id_patient_mother
    WHERE
        (tmi1.id IS NOT NULL)
            AND (tm.infant_dob BETWEEN (NOW() - INTERVAL 24 MONTH) AND (NOW() + INTERVAL 9 MONTH))
            OR (tc.dob BETWEEN (NOW() - INTERVAL 24 MONTH) AND (NOW() + INTERVAL 9 MONTH)))) li ON li.id_patient_mother = a.id_patient
    LEFT JOIN testing_mereenfant tme3 ON tme3.id_patient = li.id_patient_child
    LEFT JOIN lookup_testing_infant_arv_prophylaxis ltpx ON ltpx.id = tme3.infant_prophylaxis_arv_regime
    LEFT JOIN patient pch ON pch.id = li.id_patient_child
    LEFT JOIN lookup_testing_nutrition ltn ON ltn.id = tme3.infant_nutrition
    LEFT JOIN lookup_response lr ON lr.id = tme3.infant_prophylaxis_arv_regime_before_or_after
    LEFT JOIN (SELECT 
        id_patient
    FROM
        tracking_regime
    WHERE
        category = 'regime_mother_treatment'
            AND id_arv > 0 UNION SELECT 
        id_patient_mother AS id_patient
    FROM
        tracking_pregnancy tp
    WHERE
        tp.on_arv = 1) arv ON arv.id_patient = a.id_patient
    LEFT JOIN (SELECT 
        id_patient
    FROM
        tracking_regime
    WHERE
        category = 'regime_infant_treatment'
            AND id_arv > 0 UNION SELECT 
        id_patient
    FROM
        tracking_followup tf
    WHERE
        tf.on_arv = 1) arv_infant ON arv_infant.id_patient = li.id_patient_child
    LEFT JOIN (SELECT 
        tsp.id_patient,
            tsp.date_blood_taken,
            tsp.pcr_result,
            tsp.pcr_result_date,
            tsp.which_pcr
    FROM
        testing_specimen tsp
    WHERE
        tsp.date_blood_taken = (SELECT 
                MIN(tsp1.date_blood_taken)
            FROM
                testing_specimen tsp1
            WHERE
                tsp1.id_patient = tsp.id_patient)) sp ON sp.id_patient = tme3.id_patient
    LEFT JOIN lookup_testing_specimen_result ltsr ON ltsr.id = sp.pcr_result
    LEFT JOIN lookup_reason_termination_of_pregnancy lrtp ON lrtp.id = preg.termination_of_pregnancy_reason
    LEFT JOIN tracking_infant ti ON ti.id_patient = tme3.id_patient
    LEFT JOIN (SELECT 
        lp.*, hn.id_hospital, hn.id_network
    FROM
        lookup_hospital lp
    LEFT JOIN hospital_network hn ON hn.id_hospital = lp.id) nt ON CONCAT(nt.city_code, '/', nt.hospital_code) = LEFT(p.patient_code, 8)
    LEFT JOIN lookup_testing_which_pcr lrtw ON lrtw.id = sp.which_pcr
    LEFT JOIN lookup_testing_birth_location ltb2 ON ltb2.id = tme3.infant_birth_location
    WHERE
        p.linked_to_id_patient = 0
            AND ((a.id_patient IS NOT NULL)
            OR (sp.id_patient IS NOT NULL)
            OR (tme3.id_patient IS NOT NULL))) h
		LEFT join (
        select tmfx.id_patient, max(tmfx.date) as last_followup_date,max(tmfx.next_appointment_date) as next_appointment_date from tracking_motherfollowup tmfx
        group by tmfx.id_patient
        
        ) tf on tf.id_patient=h.id_patient
        LEFT JOIN
    (SELECT 
        opv.health_id,
            opv.is_patient_present_at_time_of_visit,
            opv.consent_of_visit_comments,
            opv.type_of_visit,
            opv.date_of_visit,
            opv.date_of_delivery AS Date_of_Delivery_Commcare,
            IF(opv.infant_received_prophylaxis = 1, 'yes', IF(opv.infant_received_prophylaxis = 2, 'No', 'Inconnu')) AS Infant_Prophylaxis_Commcare
    FROM
        (SELECT 
        health_id,
            MAX(date_of_visit) AS last_visit,
            infant_received_prophylaxis,
            date_of_delivery
    FROM
        openfn.odk_pregnancy_visit
    WHERE
        date_of_visit IS NOT NULL
    GROUP BY health_id) AS x
    INNER JOIN openfn.odk_pregnancy_visit opv ON opv.health_id = x.health_id
        AND opv.date_of_visit = x.last_visit
    GROUP BY opv.health_id) v ON h.mother_patient_code = v.health_id
        LEFT JOIN
    (SELECT 
        lh.office,
            ld.name AS departement,
            lc.name AS commune,
            ls.name AS section,
            CONCAT(lh.city_code, '/', lh.hospital_code) AS site,
            lh.name AS hospital_name,
            ln.name as network
    FROM
        lookup_hospital lh
	LEFT JOIN lookup_network ln on ln.id=lh.network
    LEFT JOIN lookup_section ls ON ls.id = lh.section
    LEFT JOIN lookup_commune lc ON lc.id = lh.commune
    LEFT JOIN lookup_departement ld ON ld.id = lc.departement) b ON h.site = b.site
GROUP BY id_patient
HAVING NOT (departement IN ('Nippes' , 'Sud', 'Sud-Est', 'Grand-Anse')
    OR office IN ('JER' , 'CAY', 'FDN', 'MIR'))
ORDER BY b.office , b.departement , b.commune , b.section , b.site
