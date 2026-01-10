import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Container,
  Paper,
  Title,
  Text,
  TextInput,
  Button,
  Stack,
  Center,
  Alert,
  Progress,
  Group,
  Checkbox,
  Loader,
  Badge,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { notifications } from '@mantine/notifications';
import {
  IconBike,
  IconMapPin,
  IconCalendar,
  IconClock,
  IconPhone,
  IconMail,
  IconAlertCircle,
} from '@tabler/icons-react';

import { eventsApi } from '../../api/client';

export default function EventPage() {
  const { slug } = useParams<{ slug: string }>();
  const [reserved, setReserved] = useState(false);
  const [tokenCode, setTokenCode] = useState<string | null>(null);

  // Fetch availability
  const { data, isLoading, error } = useQuery({
    queryKey: ['eventAvailability', slug],
    queryFn: () => eventsApi.getAvailability(slug!),
    enabled: !!slug,
  });

  const form = useForm({
    initialValues: {
      phone: '',
      email: '',
      newsletter: false,
    },
    validate: {
      phone: (value) => (value.length < 5 ? 'Inserisci un numero valido' : null),
    },
  });

  // TODO: Implement reserve mutation
  const handleSubmit = async (values: typeof form.values) => {
    // Placeholder - actual reservation will be implemented
    notifications.show({
      title: 'Prenotazione',
      message: 'Funzionalità in sviluppo',
      color: 'blue',
    });
  };

  if (isLoading) {
    return (
      <Center h="100vh">
        <Loader size="lg" />
      </Center>
    );
  }

  if (error || !data) {
    return (
      <Container size="sm" py="xl">
        <Alert icon={<IconAlertCircle size={16} />} color="red">
          Evento non trovato
        </Alert>
      </Container>
    );
  }

  const { event, availability, can_reserve, message } = data;

  if (reserved && tokenCode) {
    return (
      <Container size="sm" py="xl">
        <Center mb="xl">
          <IconBike size={64} color="var(--mantine-color-green-6)" />
        </Center>
        
        <Title ta="center" order={2} c="green">
          ✅ Prenotato!
        </Title>
        
        <Paper withBorder p="xl" mt="xl" radius="md" ta="center">
          <Text size="xl" fw={700} mb="lg">
            🎫 {tokenCode}
          </Text>
          
          <Text c="dimmed" mb="lg">
            {event.name}
          </Text>
          
          <Button fullWidth size="lg" mb="sm">
            📲 Aggiungi a Google Wallet
          </Button>
          
          <Button fullWidth variant="light">
            📤 Condividi QR
          </Button>
        </Paper>
        
        <Text ta="center" c="dimmed" mt="lg" size="sm">
          📱 QR inviato via SMS
        </Text>
      </Container>
    );
  }

  return (
    <Container size="sm" py="xl">
      <Center mb="xl">
        <IconBike size={64} color="var(--mantine-color-blue-6)" />
      </Center>
      
      <Title ta="center" order={2}>
        {event.name}
      </Title>
      
      <Stack gap="xs" mt="md" mb="xl">
        {event.location && (
          <Group justify="center" gap="xs">
            <IconMapPin size={16} />
            <Text size="sm" c="dimmed">{event.location}</Text>
          </Group>
        )}
        <Group justify="center" gap="xs">
          <IconCalendar size={16} />
          <Text size="sm" c="dimmed">
            {new Date(event.start_date).toLocaleDateString('it-IT', {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            })}
          </Text>
        </Group>
        {event.checkin_opens_at && (
          <Group justify="center" gap="xs">
            <IconClock size={16} />
            <Text size="sm" c="dimmed">
              Check-in dalle {new Date(event.checkin_opens_at).toLocaleTimeString('it-IT', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </Text>
          </Group>
        )}
      </Stack>

      {/* Availability */}
      <Paper withBorder p="md" radius="md" mb="xl">
        <Text size="sm" c="dimmed" tt="uppercase" fw={600} mb="xs">
          🅿️ Posti Disponibili
        </Text>
        <Progress
          value={availability.percent}
          size="xl"
          color={availability.percent > 80 ? 'orange' : 'blue'}
          mb="xs"
        />
        <Group justify="space-between">
          <Text size="sm" fw={500}>
            {availability.available} / {availability.total} posti
          </Text>
          <Badge color={availability.percent > 80 ? 'orange' : 'blue'}>
            {availability.percent.toFixed(0)}%
          </Badge>
        </Group>
      </Paper>

      {message && (
        <Alert color={can_reserve ? 'blue' : 'orange'} mb="xl">
          {message}
        </Alert>
      )}

      {can_reserve ? (
        <Paper withBorder p="xl" radius="md">
          <Text ta="center" mb="lg">
            Prenota il tuo posto GRATIS e salta la coda all'ingresso!
          </Text>
          
          <form onSubmit={form.onSubmit(handleSubmit)}>
            <Stack>
              <TextInput
                label="Numero di telefono"
                placeholder="+39 333 1234567"
                required
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
                label="Tienimi aggiornato su prossimi eventi"
                {...form.getInputProps('newsletter', { type: 'checkbox' })}
              />
              
              <Button type="submit" size="lg" fullWidth>
                🎫 Prenota Ora
              </Button>
              
              <Text size="xs" c="dimmed" ta="center">
                📲 Riceverai il QR via SMS
              </Text>
            </Stack>
          </form>
        </Paper>
      ) : (
        <Alert color="red" icon={<IconAlertCircle size={16} />}>
          Prenotazioni non disponibili
        </Alert>
      )}

      <Text c="dimmed" size="xs" ta="center" mt="xl">
        by Scintilla Cicloprogetti
      </Text>
    </Container>
  );
}

