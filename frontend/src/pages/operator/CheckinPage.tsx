import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Title,
  Text,
  Paper,
  Group,
  Stack,
  TextInput,
  Textarea,
  Button,
  Alert,
  Badge,
  Divider,
  Checkbox,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import {
  IconQrcode,
  IconPhone,
  IconMail,
  IconCheck,
  IconMapPin,
  IconRefresh,
} from '@tabler/icons-react';

import { eventsApi, checkinApi, adminApi, CheckinRequest, CheckinResponse } from '../../api/client';
import { useActiveEventStore } from '../../stores/activeEventStore';
import QRScanner from '../../components/common/QRScanner';

type Step = 'scan' | 'form' | 'physical';

export default function CheckinPage() {
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>('scan');
  const [scannedToken, setScannedToken] = useState<string | null>(null);
  const [isPhysicalToken, setIsPhysicalToken] = useState(false);
  const [showScanner, setShowScanner] = useState(false);
  const [bikeDescription, setBikeDescription] = useState('');
  const [lastCheckin, setLastCheckin] = useState<CheckinResponse | null>(null);

  const { eventId: activeEventId, eventName: activeEventName } = useActiveEventStore();

  const { data: nextSlot } = useQuery({
    queryKey: ['nextSlot', activeEventId],
    queryFn: () => eventsApi.getNextSlot(activeEventId!),
    enabled: !!activeEventId,
  });

  const form = useForm({
    initialValues: {
      phone: '',
      email: '',
      newsletter: false,
    },
  });

  const resetForm = () => {
    setStep('scan');
    setScannedToken(null);
    setIsPhysicalToken(false);
    setBikeDescription('');
    setLastCheckin(null);
    form.reset();
  };

  const invalidateCaches = () => {
    queryClient.invalidateQueries({ queryKey: ['checkins'] });
    queryClient.invalidateQueries({ queryKey: ['eventStats'] });
    queryClient.invalidateQueries({ queryKey: ['nextSlot'] });
  };

  const checkinMutation = useMutation({
    mutationFn: (data: CheckinRequest) => checkinApi.create(data),
    onSuccess: (response) => {
      setLastCheckin(response);
      invalidateCaches();
    },
    onError: (error: Error) => {
      notifications.show({
        title: 'Errore',
        message: error.message,
        color: 'red',
      });
    },
  });

  const reassignMutation = useMutation({
    mutationFn: (checkinId: string) => adminApi.reassignCheckin(checkinId),
    onSuccess: (response) => {
      setLastCheckin((prev) =>
        prev
          ? {
              ...prev,
              position: {
                rack_number: response.position.rack_number,
                slot_number: response.position.slot_number,
                rack_label: response.position.rack_label,
                auto_assigned: true,
              },
            }
          : prev,
      );
      notifications.show({
        title: 'Riassegnato',
        message: `Nuovo slot: ${response.position.rack_label || `Rast. ${response.position.rack_number}`}, Slot ${response.position.slot_number}`,
        color: 'blue',
      });
      invalidateCaches();
    },
    onError: (e: Error) =>
      notifications.show({ message: e.message, color: 'red' }),
  });

  const handleScan = (code: string) => {
    const tokenCode = code.includes('/t/') ? code.split('/t/')[1] : code;
    setScannedToken(tokenCode.toUpperCase());
    setShowScanner(false);
    setStep(isPhysicalToken ? 'physical' : 'form');
  };

  const handleSubmit = () => {
    if (!scannedToken && !activeEventId) {
      notifications.show({
        message: 'Seleziona un evento attivo prima di creare un nuovo token',
        color: 'red',
      });
      return;
    }
    const data: CheckinRequest = {
      token_code: scannedToken || `NEW-${Date.now()}`,
      create_token: !scannedToken,
      event_id: !scannedToken ? activeEventId || undefined : undefined,
      customer_phone: form.values.phone || undefined,
      customer_email: form.values.email || undefined,
      newsletter_opt_in: form.values.newsletter,
      physical_token: isPhysicalToken,
      auto_position: true,
      bike_description: isPhysicalToken && bikeDescription ? bikeDescription : undefined,
    };

    checkinMutation.mutate(data);
  };

  if (lastCheckin) {
    const pos = lastCheckin.position;
    const rackLabel = pos.rack_label || `Rastrelliera ${pos.rack_number}`;
    return (
      <Stack gap="lg">
        <Title order={2}>Check-in Bici</Title>
        <Paper withBorder p="xl" radius="md">
          <Stack>
            <Alert color="green" title="✅ Check-in completato!" variant="filled">
              🎫 {lastCheckin.token.code} — {rackLabel}, Slot {pos.slot_number}
            </Alert>

            <Text size="sm" c="dimmed">
              Guida il cliente alla posizione assegnata. Se lo slot è già
              occupato da un'altra bici, premi "Slot occupato" per bloccarlo
              e ottenere un nuovo slot.
            </Text>

            <Group grow>
              <Button
                variant="light"
                color="orange"
                leftSection={<IconRefresh size={18} />}
                loading={reassignMutation.isPending}
                onClick={() => reassignMutation.mutate(lastCheckin.checkin_id)}
              >
                Slot occupato, riassegna
              </Button>
              <Button
                color="green"
                leftSection={<IconCheck size={18} />}
                onClick={resetForm}
              >
                Tutto ok, prossimo
              </Button>
            </Group>
          </Stack>
        </Paper>
      </Stack>
    );
  }

  return (
    <Stack gap="lg">
      <Group justify="space-between" align="flex-end">
        <Title order={2}>Check-in Bici</Title>
        {activeEventName && (
          <Badge size="lg" variant="light" color="blue">
            {activeEventName}
          </Badge>
        )}
      </Group>

      {!activeEventId && (
        <Alert color="yellow">
          Nessun evento selezionato. Scegline uno dal menù in alto per fare check-in walk-in.
        </Alert>
      )}

      {nextSlot && (
        <Alert variant="light" color="blue" icon={<IconMapPin size={16} />}>
          Prossimo slot disponibile: <strong>{nextSlot.rack_label || `Rastrelliera ${nextSlot.rack_number}`}, Slot {nextSlot.slot_number}</strong>
        </Alert>
      )}

      {step === 'scan' && (
        <Paper withBorder p="lg" radius="md">
          <Stack>
            <Text fw={500} size="lg">🎫 Token Digitale (consigliato)</Text>

            {showScanner ? (
              <QRScanner onScan={handleScan} onClose={() => setShowScanner(false)} />
            ) : (
              <Button
                size="lg"
                leftSection={<IconQrcode size={20} />}
                onClick={() => setShowScanner(true)}
              >
                Scansiona QR Cliente
              </Button>
            )}

            <Divider label="oppure codice manuale" labelPosition="center" />

            <TextInput
              placeholder="DOT-XXXX"
              value={scannedToken || ''}
              onChange={(e) => setScannedToken(e.currentTarget.value.toUpperCase() || null)}
            />
            {scannedToken && (
              <Button onClick={() => setStep('form')}>
                Continua con {scannedToken} →
              </Button>
            )}

            <Divider label="oppure nuovo cliente (walk-in)" labelPosition="center" />

            <TextInput
              label="Telefono cliente"
              placeholder="+39 333 1234567"
              leftSection={<IconPhone size={16} />}
              {...form.getInputProps('phone')}
            />

            <TextInput
              label="Email (opzionale)"
              placeholder="mario@email.it"
              leftSection={<IconMail size={16} />}
              {...form.getInputProps('email')}
            />

            <Checkbox
              label="Iscriviti alla newsletter"
              {...form.getInputProps('newsletter', { type: 'checkbox' })}
            />

            {form.values.phone && (
              <Button onClick={() => setStep('form')}>
                Continua →
              </Button>
            )}

            <Divider />

            <Button
              variant="subtle"
              color="gray"
              onClick={() => {
                setIsPhysicalToken(true);
                setStep('physical');
              }}
            >
              📵 Cliente senza smartphone? Usa token fisico
            </Button>
          </Stack>
        </Paper>
      )}

      {step === 'form' && !isPhysicalToken && (
        <Paper withBorder p="lg" radius="md">
          <Stack>
            {scannedToken && (
              <Alert color="green" title="Token riconosciuto">
                🎫 {scannedToken}
              </Alert>
            )}

            <Paper p="md" withBorder>
              <Text fw={500} mb="sm">📍 Posizione assegnata</Text>
              {nextSlot && (
                <Badge size="lg" color="teal">
                  {nextSlot.rack_label || `Rast. ${nextSlot.rack_number}`}, Slot {nextSlot.slot_number}
                </Badge>
              )}
            </Paper>

            <Alert color="blue" variant="light">
              💡 Token digitale: nessuna foto/descrizione necessaria. Il cliente può sempre recuperare il QR tramite il suo numero di telefono.
            </Alert>

            <Group>
              <Button variant="light" onClick={() => setStep('scan')}>
                ← Indietro
              </Button>
              <Button
                flex={1}
                loading={checkinMutation.isPending}
                onClick={handleSubmit}
                leftSection={<IconCheck />}
              >
                Conferma Check-in
              </Button>
            </Group>
          </Stack>
        </Paper>
      )}

      {step === 'physical' && (
        <Paper withBorder p="lg" radius="md">
          <Stack>
            <Alert color="yellow" title="Token Fisico">
              Usa solo se il cliente NON ha smartphone disponibile.
            </Alert>

            {showScanner ? (
              <QRScanner onScan={handleScan} onClose={() => setShowScanner(false)} />
            ) : (
              <Button
                size="lg"
                color="orange"
                leftSection={<IconQrcode size={20} />}
                onClick={() => setShowScanner(true)}
              >
                Scansiona Gettone Fisico
              </Button>
            )}

            {scannedToken && (
              <>
                <Alert color="orange" title="Token scansionato">
                  🎫 {scannedToken}
                </Alert>

                <Paper p="md" withBorder>
                  <Text fw={500} mb="sm">📍 Posizione assegnata</Text>
                  {nextSlot && (
                    <Badge size="lg" color="teal">
                      {nextSlot.rack_label || `Rast. ${nextSlot.rack_number}`}, Slot {nextSlot.slot_number}
                    </Badge>
                  )}
                </Paper>

                <Textarea
                  label="Descrizione bici (opzionale)"
                  description="Utile per identificare la bici se il cliente perde il gettone."
                  placeholder="es. Bici nera mountain, cestino, luci LED"
                  maxLength={500}
                  autosize
                  minRows={2}
                  value={bikeDescription}
                  onChange={(e) => setBikeDescription(e.currentTarget.value)}
                />

                <Alert color="yellow" variant="light">
                  📋 Ricorda: consegna il gettone al cliente dopo il check-in!
                </Alert>

                <Group>
                  <Button variant="light" onClick={() => {
                    setStep('scan');
                    setScannedToken(null);
                    setIsPhysicalToken(false);
                    setBikeDescription('');
                  }}>
                    ← Indietro
                  </Button>
                  <Button
                    flex={1}
                    color="orange"
                    loading={checkinMutation.isPending}
                    onClick={handleSubmit}
                    leftSection={<IconCheck />}
                  >
                    Conferma Check-in
                  </Button>
                </Group>
              </>
            )}

            {!scannedToken && (
              <Button variant="light" onClick={() => {
                setStep('scan');
                setIsPhysicalToken(false);
              }}>
                ← Torna a token digitale
              </Button>
            )}
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}
