import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Title,
  Text,
  TextInput,
  PasswordInput,
  Button,
  Stack,
  Center,
  Alert,
} from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconBike, IconAlertCircle } from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';

import { authApi } from '../../api/client';
import { useAuthStore } from '../../stores/authStore';

export default function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const form = useForm({
    initialValues: {
      phone: '',
      pin: '',
    },
    validate: {
      phone: (value) => (value.length < 5 ? 'Inserisci un numero valido' : null),
      pin: (value) => (value.length < 4 ? 'PIN deve essere almeno 4 cifre' : null),
    },
  });

  const handleSubmit = async (values: typeof form.values) => {
    setLoading(true);
    setError(null);

    try {
      const response = await authApi.login(values.phone, values.pin);
      login(response.access_token, response.operator);
      
      notifications.show({
        title: 'Benvenuto!',
        message: `Accesso effettuato come ${response.operator.name}`,
        color: 'green',
      });
      
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore di accesso');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container size={420} my={40}>
      <Center mb="xl">
        <IconBike size={64} color="var(--mantine-color-blue-6)" />
      </Center>
      
      <Title ta="center" order={2}>
        Dottò
      </Title>
      <Text c="dimmed" size="sm" ta="center" mt={5} mb={30}>
        Sistema Valet Biciclette
      </Text>

      <Paper withBorder shadow="md" p={30} radius="md">
        <form onSubmit={form.onSubmit(handleSubmit)}>
          <Stack>
            {error && (
              <Alert
                icon={<IconAlertCircle size={16} />}
                title="Errore"
                color="red"
                variant="light"
              >
                {error}
              </Alert>
            )}

            <TextInput
              label="Numero di telefono"
              placeholder="+39 333 1234567"
              required
              {...form.getInputProps('phone')}
            />

            <PasswordInput
              label="PIN"
              placeholder="••••"
              required
              {...form.getInputProps('pin')}
            />

            <Button type="submit" fullWidth loading={loading}>
              Accedi
            </Button>
          </Stack>
        </form>
      </Paper>

      <Text c="dimmed" size="xs" ta="center" mt="xl">
        by Scintilla Cicloprogetti
      </Text>
    </Container>
  );
}

